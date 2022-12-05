from typing import Callable, Optional

from smaug.validation import base


class EqualNamedEntityCount(base.CmpBased):
    """Filters critical records that do NOT have the same named entity count.

    Args:
        ner_model: named entity recognition model to use. Should be configured
            with the correct language.
        critical_field: Field inside the perturbations dictionary with the perturbation
            to test.
    """

    def __init__(
        self,
        ner_func: Callable,
        critical_field: Optional[str] = None,
    ):
        super().__init__(critical_field=critical_field)
        self.__ner_func = ner_func

    def _verify(
        self,
        original: str,
        critical: str,
    ) -> bool:
        orig_entity_count = len(self.__ner_func(original).entities)
        crit_entity_count = len(self.__ner_func(critical).entities)
        return orig_entity_count == crit_entity_count
