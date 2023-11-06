from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Callable

from aiconfig.schema import AIConfig, ExecuteResult, Output, Prompt


if TYPE_CHECKING:
    from aiconfig.Config import AIConfigRuntime


class ModelParser(ABC):
    @abstractmethod
    def id(self) -> str:
        """
        Returns an identifier for the model (e.g. llama-2, gpt-4, etc.).
        """
        pass

    @abstractmethod
    def serialize(
        self,
        prompt_name: str,
        data: Any,
        ai_config: "AIConfigRuntime",
        parameters: Optional[Dict] = None,
        **kwargs
    ) -> Prompt:
        """
        Serialize a prompt and additional metadata/model settings into a Prompt object that can be saved in the AIConfig.

        Args:
            prompt_name (str): Name to identify the prompt.
            data (Any): The prompt data to be serialized.
            ai_config (AIConfig): The AIConfig that the prompt belongs to.
            parameters (dict, optional): Optional parameters to include in the serialization.
            **kwargs: Additional keyword arguments, if needed.

        Returns:
            Prompt: Serialized representation of the input data.
        """
        pass

    @abstractmethod
    async def deserialize(
        self,
        prompt: Prompt,
        aiConfig: "AIConfigRuntime",
        options: Optional["InferenceOptions"] = None,
        params: Optional[Dict] = None,
    ) -> Any:
        """
        Deserialize a Prompt object loaded from an AIConfig into a structure that can be used for model inference.

        Args:
            prompt (Prompt): The Prompt object from an AIConfig to deserialize into a structure that can be used for model inference.
            aiConfig (AIConfigRuntime): The AIConfig that the prompt belongs to.
            params (dict, optional): Optional parameters to override the prompt's parameters with.

        Returns:
            R: Completion params that can be used for model inference.
        """
        pass

    @abstractmethod
    async def run(
        self,
        prompt: Prompt,
        aiconfig: AIConfig,
        options: Optional["InferenceOptions"] = None,
        parameters: Dict = {},
    ) -> ExecuteResult:
        """
        Execute model inference based on completion data to be constructed in deserialize(), which includes the input prompt and
        model-specific inference settings. Saves the response or output in prompt.outputs.

        Args:
            prompt (Prompt): The prompt to be used for inference.
            aiconfig (AIConfig): The AIConfig object containing all prompts and parameters.
            options (InferenceOptions, optional): Options that determine how to run inference for the prompt
            parameters (dict, optional): Optional parameters to include in the serialization.

        Returns:
            ExecuteResult: The response generated by the model.
        """
        pass
    
    @abstractmethod
    def get_output_text(self, prompt: Prompt, aiconfig: 'AIConfigRuntime', output: Optional[Output] = None) -> str:
        """
        Get the output text from the model inference response.

        Args:
            prompt (Prompt): The prompt to be used for inference.
            aiconfig (AIConfig): The AIConfig object containing all prompts and parameters.

        Returns:
            str: The output text from the model inference response.
        """
        pass

    def get_model_settings(self, prompt: Prompt, aiconfig: "AIConfigRuntime") -> Dict[str, Any]:
        """
        Extracts the AI model's settings from the configuration. If both prompt and config level settings are defined, merge them with prompt settings taking precedence.

        Args:
            prompt: The prompt object.

        Returns:
            dict: The settings of the model used by the prompt.
        """
        if not prompt:
            return aiconfig.get_global_settings(self.id())
    
        # Check if the prompt exists in the config
        if prompt.name not in aiconfig.prompt_index or aiconfig.prompt_index[prompt.name] != prompt:
            raise IndexError(f"Prompt '{prompt.name}' not in config.")

        model_metadata = prompt.metadata.model if prompt.metadata else None
    
        if model_metadata is None:
            # Use Default Model
            default_model = aiconfig.get_default_model()
            if not default_model:
                raise KeyError(f"No default model specified in AIConfigMetadata, and prompt `{prompt.name}` does not specify a model.")
            return aiconfig.get_global_settings(default_model)
        elif isinstance(model_metadata, str):
            # Use Global settings
            return aiconfig.get_global_settings(model_metadata)
        else:
            # Merge config and prompt settings with prompt settings taking precedent
            model_settings = {}
            global_settings = aiconfig.get_global_settings(model_metadata.name)
            prompt_setings = prompt.metadata.model.settings if prompt.metadata.model.settings is not None else {}

            model_settings.update(global_settings)
            model_settings.update(prompt_setings)

            return model_settings

def print_stream_callback(data, accumulated_data, index: int):
    """
    Default streamCallback function that prints the output to the console.
    """
    print("\ndata: {}\naccumulated_data:{}\nindex:{}\n".format(data, accumulated_data, index))

def print_stream_delta(data, accumulated_data, index: int):
    """
    Default streamCallback function that prints the output to the console.
    """
    if "content" in data:
        content = data['content']
        if content:
            print(content, end = "", flush=True)


class InferenceOptions():
    """
    Options that determine how to run inference for the prompt (e.g., whether to stream the output or not, callbacks, etc.)
    """

    def __init__(self, stream_callback: Callable[[Any, Any, int], Any] = print_stream_delta,  stream=True, **kwargs ):
        super().__init__()

        """ 
        Called when a model is in streaming mode and an update is available.

        Args:
            data: The new data chunk from the stream.
            accumulatedData: The running sum of all data chunks received so far.
            index (int): The index of the choice that the data chunk belongs to
                (default is 0, but if the model generates multiple choices, this will be the index of
                the choice that the data chunk belongs to).

            Returns:
                None
        """
        self.stream_callback = stream_callback
        
        self.stream = stream

        for key, value in kwargs.items():
            setattr(self, key, value)

    def update_stream_callback(self, callback: Callable[[Any, Any, int], Any]):
        """
        Update the streamCallback function in the callbacks dictionary.
        """
        self.stream_callback= callback