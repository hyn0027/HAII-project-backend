from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from typing import Iterable, Set
import re


class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=128)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return self.username


class KeywordExplanationPair(models.Model):
    keyword = models.CharField(max_length=100)
    explanation = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.keyword}: {self.explanation}"

    @classmethod
    def get_keyword_explanation_pair_list_from_model_res(
        cls,
        model_res,
    ) -> Iterable["KeywordExplanationPair"]:
        res = []
        for item in model_res:
            keyword = item.get("word", "").strip()
            explanation = item.get("explanation", "").strip()
            if keyword != "" and explanation != "":
                res.append(
                    KeywordExplanationPair(keyword=keyword, explanation=explanation)
                )
        return res


class Passage(models.Model):
    split_result = models.JSONField(null=True, blank=True)
    split_result_with_explanations = models.JSONField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    @classmethod
    def from_split_result(cls, split_result) -> "Passage":
        passage = cls()
        passage.split_result = split_result
        passage.split_result_with_explanations = []
        for paragraph in split_result or []:
            para_with_explanations = []
            for word in paragraph:
                para_with_explanations.append({"word": word, "explanation": ""})
            passage.split_result_with_explanations.append(para_with_explanations)
        return passage

    @classmethod
    def from_split_result_with_explanations(
        cls, split_result_with_explanations
    ) -> "Passage":
        passage = cls()
        passage.split_result_with_explanations = split_result_with_explanations
        passage.split_result = []
        for paragraph in split_result_with_explanations or []:
            para_words = []
            for word_obj in paragraph:
                para_words.append(word_obj.get("word", ""))
            passage.split_result.append(para_words)
        return passage

    def apply_explanations(self, explanations: Iterable[KeywordExplanationPair]):
        if not self.split_result:
            return

        for item in explanations:
            keyword = item.keyword
            explanation = item.explanation
            for paragraph in self.split_result_with_explanations:
                for word_obj in paragraph:
                    if word_obj["word"].lower().strip() == keyword.lower().strip():
                        word_obj["explanation"] = explanation

    def get_word_set_from_split_result(self) -> Set[str]:
        word_set = set()
        if not self.split_result:
            return word_set

        for paragraph in self.split_result:
            for word_obj in paragraph:
                if word_obj.strip() != "" and not re.match(
                    r'^[\.,\?\:"\(\);\!\[\]\{\}<>]+$', word_obj
                ):
                    word_set.add(word_obj.lower().strip())
        return word_set
