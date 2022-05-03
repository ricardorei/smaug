import functools
import re
import stanza
import torch
import transformers

from typing import List, Optional, Tuple, Union

from maug import random


_PERTURB_TOK = "<|perturb|>"
_BLANK_TOK = "[BLANK]"
_SEP_TOK = "[SEP]"
_EMPTY_TOK = "[EMPTY]"
_ANSWER_TOK = "[ANSWER]"
_EOF_TOKEN = "<|endoftext|>"

_NEGATION = "[negation]"

SingleNegPolyjuiceInput = str
SingleNegPolyjuiceOutput = Tuple[str, Optional[str]]

NegPolyjuiceInput = Union[SingleNegPolyjuiceInput, List[SingleNegPolyjuiceInput]]
NegPolyjuiceOutput = Union[SingleNegPolyjuiceOutput, List[SingleNegPolyjuiceOutput]]


class NegPolyjuice:
    """Polyjuice model conditioned on negation.

    This model wraps the Polyjuice model presented in the paper
    "Polyjuice: Generating Counterfactuals for Explaining, Evaluating, and Improving Models"
    from Tongshuang Wu, Marco Tulio Ribeiro, Jeffrey Heer, Daniel S. Weld
    at the Association for Computational Linguistics (ACL), 2021.
    The code for this model is available at https://github.com/tongshuangwu/polyjuice.

    This model conditions the previous model for negation, by masking verbs.
    It tries to mask also auxiliary verbs with a given verb.

    POS tagging is performed with the stanza POS tagger.

    Args:
        cuda: Whether to usa a cuda enabled gpu or not.
    """

    def __init__(self, cuda: bool = False):
        self.__stanza_pos = self.__load_stanza_pos(cuda)
        polyjuice_model, polyjuice_tokenizer = self.__load_polyjuice()
        self.__pad_token_id = polyjuice_tokenizer.convert_tokens_to_ids(_EOF_TOKEN)
        self.__polyjuice = transformers.pipeline(
            "text-generation",
            model=polyjuice_model,
            tokenizer=polyjuice_tokenizer,
            framework="pt",
            device=0 if cuda else -1,
        )
        self.__rng = random.numpy_seeded_rng()

    @functools.singledispatchmethod
    def __call__(self, text: NegPolyjuiceInput) -> NegPolyjuiceOutput:
        raise NotImplementedError(f"Not implemented for type {type(text)}")

    @__call__.register
    def _(self, text: SingleNegPolyjuiceInput) -> SingleNegPolyjuiceOutput:
        return self.__generate([text])[0]

    @__call__.register
    def _(self, text: list) -> List[SingleNegPolyjuiceOutput]:
        return self.__generate(text)

    def __generate(
        self, text: List[SingleNegPolyjuiceInput]
    ) -> List[SingleNegPolyjuiceOutput]:
        sentences_with_prompts = [(s, self.__add_negation_prompt(s)) for s in text]
        prompts = [p for _, p in sentences_with_prompts if p is not None]
        with torch.no_grad():
            generation_out = self.__polyjuice(
                prompts,
                num_beams=5,
                early_stopping=True,
                pad_token_id=self.__pad_token_id,
                max_length=1000,
                do_sample=False,
                no_repeat_ngram_size=2,
            )

        # We have a result for each prompt, but not for each original
        # sentence.
        results = (self.__extract_results(g)[0] for g in generation_out)

        return [
            # Replace prompt with result if prompt existed
            next(results) if p is not None else None
            for _, p in sentences_with_prompts
        ]

    def __add_negation_prompt(self, doc: str) -> Optional[str]:
        tagged = self.__stanza_pos(doc)
        possible_mask_intervals = []
        for sentence in tagged.sentences:
            for i, _ in enumerate(sentence.words):
                interval = self.__get_prev_aux_if_verb(sentence, i)
                if interval:
                    possible_mask_intervals.append(interval)
                interval = self.__get_verb_if_verb(sentence, i)
                if interval:
                    possible_mask_intervals.append(interval)

        if not possible_mask_intervals:
            return None
        mask_start, mask_end = self.__rng.choice(possible_mask_intervals)
        masked = f"{doc[:mask_start]}{_BLANK_TOK}{doc[mask_end:]}"
        return f"{doc} {_PERTURB_TOK} {_NEGATION} {masked} {_SEP_TOK}"

    @staticmethod
    def __extract_results(single_output):
        results = []
        for option in single_output:
            prompt, answers = option["generated_text"].split(_SEP_TOK)
            _, phrase_with_blank = prompt.split(_NEGATION)
            answers = [x.strip() for x in answers.split(_ANSWER_TOK)][:-1]
            answers = [x if x != _EMPTY_TOK else "" for x in answers]
            for a in answers:
                if a == "":
                    phrase_with_blank = re.sub(
                        r" %s" % re.escape(_BLANK_TOK), a, phrase_with_blank, count=1
                    )
                else:
                    phrase_with_blank = re.sub(
                        r"%s" % re.escape(_BLANK_TOK), a, phrase_with_blank, count=1
                    )
            results.append(phrase_with_blank.strip())
        return results

    @staticmethod
    def __get_prev_aux_if_verb(sentence, i) -> Optional[Tuple]:
        if sentence.words[i].upos != "VERB" or i == 0:
            return None
        last_aux_idx = i
        while last_aux_idx > 0 and sentence.words[last_aux_idx - 1].upos == "AUX":
            last_aux_idx -= 1
        if last_aux_idx == i:
            return None
        return (sentence.words[last_aux_idx].start_char, sentence.words[i].end_char)

    @staticmethod
    def __get_verb_if_verb(sentence, i) -> Optional[Tuple]:
        word = sentence.words[i]
        if word.upos != "VERB":
            return None
        return (word.start_char, word.end_char)

    @staticmethod
    def __load_stanza_pos(use_gpu):
        processors = "tokenize,pos"
        stanza.download(lang="en", processors=processors, logging_level="WARN")
        return stanza.Pipeline(lang="en", processors=processors, use_gpu=use_gpu)

    @staticmethod
    def __load_polyjuice():
        model_path = "uw-hai/polyjuice"
        model = transformers.AutoModelForCausalLM.from_pretrained(model_path)
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            model_path, pad_token=_EOF_TOKEN
        )
        return model, tokenizer
