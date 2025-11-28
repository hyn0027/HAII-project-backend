from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.sessions.models import Session
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .llm_interface import call_model_with_json_response
from .models import KeywordExplanationPair, Passage, User
from .profile import get_user_from_session
import random


@method_decorator(csrf_exempt, name="dispatch")
class KeywordView(APIView):
    def _split_passage(self, doc) -> Passage:
        system_prompt = (
            "You are an article analysis assistant. "
            "You will be provided with a passage from an article. "
            "Your task is split the passage into a list of semantic words or phrases. "
            "You should separate out punctuation marks, articles such as a/an/the, pronouns such as he/she/it/they, and conjunctions such as and/but/or, as individual items in the list. "
            "For other words or phrases, you should group them together based on their semantic meaning. "
            "If there is a line break, you should represent it as a '\\n' item in the list.\n\n"
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

        user_bio = user.bio if user.bio else "General audience"
        user_known_words = user.known_keywords if user.known_keywords else []
        sample_known_words = ", ".join(
            random.sample(user_known_words, min(200, len(user_known_words)))
        )

        system_prompt = (
            "You are an word explanation assistant. "
            "You will be provided with a list of words or phrases from an article. "
            "Your task is to assess if each word or phrase is difficult for an user to understand. "
            "A word or phrase should be considered difficult for the user to understand if it includes technical jargon, domain-specific terminology, abbreviations, or uncommon words that is not in the user's field.\n\n"
            f"To help you better understand the user's need, here is some information about the user:\n"
            "User bio:\n"
            '"""'
            f"{user_bio}\n"
            '"""\n'
            "Terminologies the user is ALREADY familiar with: "
            '"""'
            f"{sample_known_words}\n"
            '"""\n\n'
            "You should make reasonable assumptions about the user's background and knowledge based on the provided bio and the terminologies they are already familiar with. "
            "Do not consider a word or phrase as difficult if it is likely to be understood by the user given their background and known terminologies.\n\n"
            "For each identified term that the user may not understand, provide a brief and clear explanation suitable for a general audience. "
            "Ensure explanations are concise, accurate, and avoid using further technical jargon.\n\n"
            "Format the output as a JSON objects. Each object should contain 3 fields: "
            "'word' (the identified term), 'explanation' (its definition or meaning in simple language), and 'reason' (a brief explanation of why this term is difficult for the user to understand).\n\n"
            "The following example illustrates the input-output format:\n\n"
            "Example input:\n"
            '"""\n'
            "Keyword1\n"
            "Keyword2\n"
            "Keyword3\n"
            "Keyword4\n"
            "Keyword5\n"
            "Keyword6\n"
            "Keyword7\n"
            '"""\n\n'
            "Expected output:\n"
            "{\n"
            '  "result": [\n'
            '    {"word": "Keyword1", "explanation": "Explanation for Keyword1.", "reason": "Reason why Keyword1 is difficult for this particilar user."},\n'
            '    {"word": "Keyword3", "explanation": "Explanation for Keyword3.", "reason": "Reason why Keyword3 is difficult for this particilar user."},\n'
            '    {"word": "Keyword7", "explanation": "Explanation for Keyword7.", "reason": "Reason why Keyword7 is difficult for this particilar user."},\n'
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

        return Response(
            {"keywords_with_explanations": passage.split_result_with_explanations},
            status=status.HTTP_200_OK,
        )


class GetAIExplanationView(APIView):
    SAMPLE_PASSAGE = (
        "Computer Science: Segment trees are a data structure useful for dynamic interval queries.\n"
        "Medicine: Hypertension, or high blood pressure, is a common condition that increases the risk of heart disease and stroke.\n"
        "Mathematics: A prime number is a natural number greater than 1 that cannot be formed by multiplying two smaller natural numbers.\n"
        "Biology: Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods with the help of chlorophyll.\n"
        "Physics: Quantum mechanics is a fundamental theory in physics that provides a description of the physical properties of nature at the scale of atoms and subatomic particles.\n"
        "Economics: Inflation is the rate at which the general level of prices for goods and services is rising, leading to a decrease in purchasing power.\n"
        "History: The Renaissance was a period in European history marking the transition from the Middle Ages to modernity, characterized by a revival of art, culture, and intellectual pursuit.\n"
        "Art: Cubism is an early-20th-century avant-garde art movement that revolutionized European painting and sculpture by introducing abstracted forms and multiple perspectives.\n"
        "Chemistry: An acid is a molecule or ion capable of donating a proton (hydrogen ion) or forming a covalent bond with an electron pair.\n"
        "Geography: A delta is a landform that forms at the mouth of a river, where the river splits into several outlets to enter a larger body of water, often creating a triangular shape.\n"
        "Literature: Metaphor is a figure of speech that involves an implicit comparison between two unlike things, suggesting they are alike in a certain way."
    )

    def get(self, request):
        request.data["passage"] = self.SAMPLE_PASSAGE

        response = InitialKeywordView().post(request)
        response.data["sample_passage"] = self.SAMPLE_PASSAGE
        return Response(response.data, status=response.status_code)


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


class SavePassageView(APIView):
    def post(self, request):
        # Check authentication
        user = get_user_from_session(request)
        if not user:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        keywords_with_explanations = request.data.get("keywords_with_explanations", [])

        passage = Passage.from_split_result_with_explanations(
            keywords_with_explanations
        )
        passage.user = user
        passage.save()

        return Response(
            {"message": "Passage saved successfully"}, status=status.HTTP_200_OK
        )


class GetSavedPassagesView(APIView):
    def get(self, request):
        # Check authentication
        user = get_user_from_session(request)
        if not user:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        passages = Passage.objects.filter(user=user).order_by("-created_at")
        passages_data = []
        for passage in passages:
            passages_data.append(
                {
                    "id": passage.id,
                    "split_result": passage.split_result,
                    "split_result_with_explanations": passage.split_result_with_explanations,
                }
            )

        return Response({"passages": passages_data}, status=status.HTTP_200_OK)


class DeleteSavedPassageView(APIView):
    def post(self, request):
        # Check authentication
        user = get_user_from_session(request)
        if not user:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        passage_id = request.data.get("passage_id", "")
        if not passage_id:
            return Response(
                {"error": "No passage_id provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            passage = Passage.objects.get(id=passage_id, user=user)
            passage.delete()
            return Response(
                {"message": "Passage deleted successfully"}, status=status.HTTP_200_OK
            )
        except Passage.DoesNotExist:
            return Response(
                {"error": "Passage not found"}, status=status.HTTP_404_NOT_FOUND
            )
