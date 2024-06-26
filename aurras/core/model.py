import json
import pandas as pd
import tensorflow as tf
from transformers import TFDistilBertModel, DistilBertTokenizerFast
from .prompt_processing import encode, encode_without_labels, safe_eval


class Model:
    def __init__(self, intent_labels_path: str, entity_labels_path: str, padding: int):
        """
        Initialize the model class

        Inputs:
        - intent_labels_path: Path to the intent_labels json file
        - entity_labels_path: Path to the entity_labels json file
        - padding:            Maximum number of encoded tokens in a given sequence
        """

        self.intent_labels = json.load(open(intent_labels_path, "r"))
        self.entity_labels = json.load(open(entity_labels_path, "r"))

        self.intent_class_count = len(self.intent_labels)
        self.entity_class_count = len(self.entity_labels)
        self.padding = padding

    def build_model(self, model_name: str, random_seed: int = 42):
        """
        Builds the intent and sequence classification model with keras' model API.

        Inputs:
         - model_name:  The huggingface transformer to use.  Distilbert-base-uncased is recommended
         - random_seed: The selected random seed for reproducible results

        Outputs:
         - saves the uncompiled model to the class
        """

        # define the tokenizer
        self.tokenizer = DistilBertTokenizerFast.from_pretrained(model_name)

        # build the nlp model
        weight_initializer = tf.keras.initializers.GlorotNormal(seed=random_seed)

        # * inputs
        input_ids_layer = tf.keras.layers.Input(
            shape=(self.padding), name="input_ids", dtype="int32"
        )
        input_attention_layer = tf.keras.layers.Input(
            shape=(self.padding), name="input_attention", dtype="int32"
        )

        # * transformer
        transformer = TFDistilBertModel.from_pretrained(model_name)
        last_hidden_state = transformer([input_ids_layer, input_attention_layer])[
            0
        ]  # (batch_size, sequence_length, hidden_size=768)

        # * outputs
        cls_token = last_hidden_state[:, 0, :]

        intent_output = tf.keras.layers.Dense(
            self.intent_class_count,
            activation="softmax",
            kernel_initializer=weight_initializer,
            kernel_constraint=None,
            bias_initializer="zeros",
            name="intent",
        )(cls_token)

        entity_output = tf.keras.layers.Dense(
            256,
            activation="relu",
            kernel_initializer=weight_initializer,
            kernel_constraint=None,
            bias_initializer="zeros",
        )(last_hidden_state)

        entity_output = tf.keras.layers.Dense(
            self.entity_class_count,
            activation="softmax",
            kernel_initializer=weight_initializer,
            kernel_constraint=None,
            bias_initializer="zeros",
            name="entities",
        )(entity_output)

        # define the model
        self.model = tf.keras.Model(
            [input_ids_layer, input_attention_layer], [intent_output, entity_output]
        )
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=5e-5),
            loss=tf.keras.losses.CategoricalCrossentropy(),
            metrics=tf.keras.metrics.CategoricalAccuracy("categorical_accuracy"),
        )

    def train(self, dataset_path: str, epochs: int, batch_size: int = 16):
        """
        Train the model on a dataset generated by the data_processing.generate_dataset function

        Inputs:
         - dataset_path: path to the dataset .pkl file
         - epochs:       number of epochs to train for
         - batch_size:   model batch size
        """

        # load in the dataset
        df_train = pd.read_csv(dataset_path)

        df_train['word_entities'] = df_train['word_entities'].apply(safe_eval)

        # prepare model inputs
        x_train_ids, x_train_attention, y_train_entities = encode(
            self.tokenizer,
            list(df_train["prompts"]),
            list(df_train["word_entities"]),
            max_len=self.padding,
        )

        # prepare model outputs
        y_train_intents = tf.one_hot(
            df_train["prompt_intent"].values, self.intent_class_count
        )
        y_train_entities = tf.one_hot(y_train_entities, self.entity_class_count)

        # train the model
        history = self.model.fit(
            x=[x_train_ids, x_train_attention],
            y=[y_train_intents, y_train_entities],
            epochs=epochs,
            batch_size=batch_size,
            verbose=1,
        )

        # print(f'{json.dumps(history.history)}')

    def load_model(self, model_path: str, model_name: str):
        """
        Load in a pre-trained model

        Inputs:
         - model_path: Path to the weights of the pre-trained model
         - model_name: The huggingface transformer to use.  Distilbert-base-uncased is recommended

        """

        self.build_model(model_name)
        self.model.load_weights(model_path)

    def save_model(self, model_path: str):
        """
        Save the model's weights to a directory

        Inputs:
         - model_path: directory to save the weights in
        """

        self.model.save_weights(model_path)

    def classify(self, text: str, max_len: int) -> object:
        """
        Classify a single text prompt

        Inputs:
         - text: prompt to classify
         - max_len: encoded length of a prompt

        Outputs:
         - info: json object containing decoded predictions (entities & intents)
        """

        input = encode_without_labels(self.tokenizer, text, max_len)
        model_output = self.model(input)

        info = self.__decode_prediction(input[0][0], model_output)

        return info

    """ Private """

    def __decode_prediction(self, input_ids, model_output) -> object:
        """
        Decodes a raw model output

        Inputs:
         - input_ids: tokenized input prompt
         - model_output: raw model output

        Outputs:
         - info: Json containing the intent and all entities
        """

        # extract classifications from the model output
        intent_classification = model_output[0]
        intent_id = intent_classification.numpy().argmax(axis=1)[0]

        entity_classifications = model_output[1]
        entity_ids = entity_classifications.numpy().argmax(axis=2)[0]

        # form the return json
        info = {"intent": self.intent_labels[str(intent_id)], "entities": []}

        current_entity = []
        current_entity_label = -1

        # loop over each token and add it to the info dict if it's been labled
        for i in range(len(input_ids)):
            token_id = input_ids[i]
            token_label = entity_ids[i]

            if token_label == current_entity_label:  # more of the current entity
                current_entity.append(token_id)
            else:
                # the entity is done - add it to the info dict
                if current_entity_label != -1:
                    info["entities"].append(
                        (
                            self.entity_labels[str(current_entity_label)],
                            self.tokenizer.decode(current_entity),
                        )
                    )
                    current_entity_label = -1

                if token_label != 0:  # a new entity
                    current_entity_label = token_label
                    current_entity = [token_id]

        return info