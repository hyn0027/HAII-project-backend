from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.sessions.models import Session
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .llm_interface import call_model_with_json_response
from .models import KeywordExplanationPair, Passage, User
from .profile import get_user_from_session


@method_decorator(csrf_exempt, name="dispatch")
class KeywordView(APIView):
    def _split_passage(self, doc) -> Passage:
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

        res = [[]]
        for word in model_res:
            if word == "\n":
                res.append([])
            else:
                res[-1].append(word)
        return Passage.from_split_result(res)


class InitialKeywordView(KeywordView):
    def post(self, request):
        # Check authentication
        user = get_user_from_session(request)
        if not user:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        passage = request.data.get("passage", "")
        if not passage:
            return Response(
                {"error": "No passage provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        passage = self._split_passage(passage)
        passage.user = user

        word_set = passage.get_word_set_from_split_result()

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
        keyword_explanation_pairs = (
            KeywordExplanationPair.get_keyword_explanation_pair_list_from_model_res(
                model_res.get("result", [])
            )
        )

        for pair in keyword_explanation_pairs:
            pair.user = user
            pair.save()

        passage.apply_explanations(user.get_all_keyword_explanation_pairs())

        # passage.save()

        return Response(
            {"keywords_with_explanations": passage.split_result_with_explanations},
            status=status.HTTP_200_OK,
        )


class NewKeywordView(KeywordView):
    def post(self, request):
        # Check authentication
        user = get_user_from_session(request)
        if not user:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        keywords_with_explanations = request.data.get("keywords_with_explanations", [])
        requested_word = request.data.get("requested_word", "")

        if not requested_word:
            return Response(
                {"error": "No requested_word provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        passage = Passage.from_split_result_with_explanations(
            keywords_with_explanations
        )
        passage.user = user

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

        # Create and save keyword explanation with user association
        keyword_explanation_pairs = [
            KeywordExplanationPair(
                keyword=requested_word,
                explanation=model_res.get("result", [])[0].get("explanation", ""),
                user=user,
            )
        ]

        user.delete_known_word(requested_word)

        # Save the new keyword explanation
        for pair in keyword_explanation_pairs:
            pair.save()

        passage.apply_explanations(user.get_all_keyword_explanation_pairs())
        # passage.save()

        return Response(
            {"keywords_with_explanations": passage.split_result_with_explanations},
            status=status.HTTP_200_OK,
        )


class AddKnownKeywordView(APIView):
    def post(self, request):
        # Check authentication
        user = get_user_from_session(request)
        if not user:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        word = request.data.get("word", "")
        if not word:
            return Response(
                {"error": "No word provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        user.add_known_word(word)

        keywords_with_explanations = request.data.get("keywords_with_explanations", [])

        passage = Passage.from_split_result_with_explanations(
            keywords_with_explanations
        )
        passage.user = user

        passage.apply_explanations(user.get_all_keyword_explanation_pairs())

        return Response(
            {"keywords_with_explanations": passage.split_result_with_explanations},
            status=status.HTTP_200_OK,
        )
