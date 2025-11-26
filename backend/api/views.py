from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import re
from .llm_interface import call_model_with_json_response


class KeywordView(APIView):
    def _split_passage(self, doc):
        # ask a model, split the passage into keyword list
        system_prompt = (
            "You are an article analysis assistant. "
            "You will be provided with a passage from an article. "
            "Your task is split the passage into a list of semantic words or phrases. "
            "Format the output as a JSON object.\n\n"
            "Example input:\n"
            '"""\n'
            "Segment trees is useful. It is a data structure. \n"
            "It is efficient for dynamic interval queries.\n"
            '"""\n\n'
            "Expected output:\n"
            '"""\n'
            "{\n"
            '  "result": [\n'
            '    "Segment trees",\n'
            '    "is",\n'
            '    "useful",\n'
            '    ".",\n'
            '    "It",\n'
            '    "is",\n'
            '    "a",\n'
            '    "data structure",\n'
            '    ".",\n'
            '    "\\n",\n'
            '    "It",\n'
            '    "is",\n'
            '    "efficient",\n'
            '    "for",\n'
            '    "dynamic",\n'
            '    "interval queries",\n'
            '    "."\n'
            "  ]\n"
            "}\n"
            '"""'
        )
        model_res = call_model_with_json_response(
            system_prompt=system_prompt, user_prompt=doc
        )
        model_res = model_res.get("result", [])

        # split by '\n'
        res = [[]]
        for word in model_res:
            if word == "\n":
                res.append([])
            else:
                res[-1].append({"word": word})
        return res

    def _get_word_set_from_split_result(self, split_res):
        word_set = set()
        for paragraph in split_res:
            for word_obj in paragraph:
                if word_obj["word"].strip() != "" and not re.match(
                    r'^[\.,\?\:"\(\);\!\[\]\{\}<>]+$', word_obj["word"]
                ):
                    word_set.add(word_obj["word"])
        return word_set

    def post(self, request):
        passage = request.data.get("passage", "")
        if not passage:
            return Response(
                {"error": "No passage provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        split_res = self._split_passage(passage)
        word_set = self._get_word_set_from_split_result(split_res)
        print("Split result:", split_res)
        print("Word set:", word_set)

        system_prompt = (
            "You are an word explanation assistant targeting a general audience. "
            "You will be provided with a list of words or phrases from a technical article. "
            "Your task is to assess if each word or phrase may be difficult for a general audience who does not have a technical background to understand. \n\n"
            "A word or phrase should be considered difficult if it includes technical jargon, domain-specific terminology, abbreviations, or uncommon words.\n\n"
            "For each identified difficult term, provide a brief and clear explanation suitable for a general audience. "
            "Ensure explanations are concise, accurate, and avoid using further technical jargon.\n\n"
            "Format the output as a JSON objects. Each object should contain two fields: "
            "'word' (the identified term) and 'explanation' (its definition or meaning in simple language).\n\n"
            "Example input:\n"
            '"""\n'
            "Segment trees\n"
            "useful\n"
            "It\n"
            "data structure\n"
            "a\n"
            "dynamic\n"
            "easy\n"
            "interval queries\n"
            '"""\n\n'
            "Expected output:\n"
            "{\n"
            '  "result": [\n'
            '    {"word": "Segment trees", "explanation": "A segment tree is a binary tree data structure used for storing information about intervals or segments. It allows efficient querying and updating of interval data."},\n'
            '    {"word": "data structure", "explanation": "A data structure is a way of organizing and storing data in a computer so that it can be accessed and modified efficiently."},\n'
            '    {"word": "dynamic", "explanation": "In computer science, dynamic refers to something that can change size or structure while a program is running."},\n'
            '    {"word": "interval queries", "explanation": "An interval query is a request for information about a specific range of values, often used in databases or data structures."}\n'
            "  ]\n"
            "}\n"
            '"""'
        )

        model_res = call_model_with_json_response(
            system_prompt=system_prompt, user_prompt="\n".join(word_set)
        )
        for item in model_res.get("result", []):
            word = item["word"]
            explanation = item["explanation"]
            for paragraph in split_res:
                for word_obj in paragraph:
                    if word_obj["word"] == word:
                        word_obj["explanation"] = explanation
        return Response(
            {"keywords_with_explanations": split_res}, status=status.HTTP_200_OK
        )


class NewKeywordView(APIView):
    def post(self, request):
        keywords_with_explanations = request.data.get("keywords_with_explanations", [])
        requested_word = request.data.get("requested_word", "")

        system_prompt = (
            "You are an word explanation assistant targeting a general audience. "
            "You will be provided with a words or phrases from a technical article. "
            "Your task is to provide a brief and clear explanation suitable for a general audience. "
            "Ensure explanations are concise, accurate, and avoid using further technical jargon.\n\n"
            "Format the output as a JSON objects. Each object should contain two fields: "
            "'word' (the identified term) and 'explanation' (its definition or meaning in simple language).\n\n"
            "Example input:\n"
            '"""\n'
            "Segment trees\n"
            '"""\n\n'
            "Expected output:\n"
            "{\n"
            '  "result": [\n'
            '    {"word": "Segment trees", "explanation": "A segment tree is a binary tree data structure used for storing information about intervals or segments. It allows efficient querying and updating of interval data."},\n'
            "  ]\n"
            "}\n"
            '"""'
        )
        model_res = call_model_with_json_response(
            system_prompt=system_prompt, user_prompt=requested_word
        )
        for item in model_res.get("result", []):
            word = item["word"]
            explanation = item["explanation"]
            for paragraph in keywords_with_explanations:
                for word_obj in paragraph:
                    if word_obj["word"] == word:
                        word_obj["explanation"] = explanation
        return Response(
            {"keywords_with_explanations": keywords_with_explanations},
            status=status.HTTP_200_OK,
        )
