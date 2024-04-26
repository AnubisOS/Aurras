from .core.model import Model

# interactions
from .core.plugins import PluginManager

try:
    from .dataset.dataset import Dataset
except : 
    pass 

import tomllib as toml 

from pkg_resources import Requirement, resource_filename

class Aurras:

    """PUBLIC"""

    def __init__(self, config_file= resource_filename(Requirement.parse("aurras"),"config.toml")): #! NEED FIX  config file default path 
        """Initialize all integration classes & prepare Aurras for general use"""
        self.nlp = None
        self.Config = toml.load(open(config_file, "rb"))
        print("Initializing Aurras...")

        self.plugins = PluginManager(self.Config.get("data").get("PLUGINS_PATH"))
        self.intent_label_path = f"{self.Config.get('data').get('DATASET_PATH')}/intent_labels.json"
        self.entity_label_path = f"{self.Config.get('data').get('DATASET_PATH')}/entity_labels.json"
        self.dataset_path = f"{self.Config.get('data').get('DATASET_PATH')}/dataset.csv"


    def load(self):
        """Load in a pre-trained NLP model"""

        print("Loading Aurras...")

        self.nlp = Model(self.intent_label_path, self.entity_label_path, self.Config.get('data').get('DATASET_PATH'))
        self.nlp.load_model(self.Config.get('model').get('PRETRAINED_PATH'), 
        self.Config.get('data').get('MODEL_NAME'))

    def build(self):
        """Build & train Aurras' NLP model"""
        print("Building Aurras...")

        self.nlp = Model(self.intent_label_path, self.entity_label_path, self.Config.get('data').get('PROMPT_PADDING'))
        self.nlp.build_model(self.Config.get('data').get('MODEL_NAME'))
        self.nlp.train(self.Config.get('data').get('DATASET_PATH'), epochs=self.Config.get('training').get('EPOCHS'))
        self.nlp.save_model(self.Config.get('model').get('PRETRAINED_PATH'))

    def build_dataset(self):
        """Build a dataset based on the provided intents & entities"""
        print("Generating a dataset...")

        dataset = Dataset(
            self.Config.get('data').get('DATASET_PATH'),
            self.Config.get('data').get('SAMPLES_PER_INTENT'),
            self.Config.get('data').get('ALLOW_DUPLICATE_SAMPLES')
        )
        dataset.load()
        dataset.genrate_dataset()
        dataset.save(
            self.Config.get('data').get('DATASET_PATH')
        )

    def get_classification(self, prompt: str) -> dict:
        """
        Get the classification of a single prompt

        Outputs:
         - classification: Classification json containing intent and extracted entities
        """

        classification = self.nlp.classify(prompt)

        return classification

    def ask(self, prompt: str) -> dict:
        """
        Pass a single prompt to Aurras

        Outputs:
         - response: Response json object
        """

        classification = self.nlp.classify(prompt, self.Config.get('data').get('PROMPT_PADDING'))
        response = self.plugins.generate_response(
            classification["intent"], classification["entities"], prompt
        )

        return response

    def interact(self):
        """Start a conversation with Aurras - text based"""
        print("\n\n")
        print("Live interactive console loaded")

        while True:
            # get the user's prompt
            print("=> ", end="")
            prompt = input()

            if prompt.lower().strip() == "exit":  # exit case
                break

            response = self.ask(prompt)
            print(response["response"])
            print("")

    def parse_speech(self, speech):
        """
        Parses an audio clip and extracts the speech

        Inputs:
         - speech (Not yet decided)

        Outputs:
         - text : 
        """
        return

    def generate_speech(self, text: str):
        """
        Generate an audio clip of the provided text

        Inputs:
         - text (string)

        Outputs:
         - speech (path): Path to audio file
        """
        return