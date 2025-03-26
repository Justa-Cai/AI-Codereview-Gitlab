from abc import abstractmethod
from typing import List, Dict, Optional

from biz.llm.types import NotGiven, NOT_GIVEN


class BaseClient:
    """ Base class for chat models client. """

    @abstractmethod
    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    temperature: float = 0.7,
                    max_tokens: Optional[int] = None,
                    ) -> str:
        """Chat with the model.
        """
        pass

    @abstractmethod
    def stream_completions(self,
                          messages: List[Dict[str, str]],
                          model: Optional[str] | NotGiven = NOT_GIVEN,
                          temperature: float = 0.7,
                          max_tokens: Optional[int] = None,
                          ) -> str:
        """Stream chat with the model.
        """
        pass
