from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json
import re
from .llm_interface import call_openai_model


class KeywordView(APIView):
    def post(self, request):
        passage = request.data.get("passage", "")
        if not passage:
            return Response(
                {"error": "No passage provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        system_prompt = (
            "You are an article analysis assistant. "
            "You will be provided with a passage from a technical article. "
            "Your task is to identify words or phrases that may be difficult for a general audience to understand. "
            "These include technical jargon, domain-specific terminology, abbreviations, and uncommon words.\n\n"
            "For each identified term, provide a brief and clear explanation suitable for a general audience. "
            "Ensure explanations are concise, accurate, and avoid using further technical jargon.\n\n"
            "Format the output as a JSON array of objects. Each object should contain two fields: "
            "'word' (the identified term) and 'explanation' (its definition or meaning in simple language).\n\n"
            "Example input:\n"
            '"""\n'
            "Segment trees is useful. It is widely used. \n"
            "It is efficient for dynamic interval queries.\n"
            '"""\n\n'
            "Expected output:\n"
            "[\n"
            '  {"word": "Segment trees", "explanation": "A segment tree is a binary tree data structure used for storing information about intervals or segments. It allows efficient querying and updating of interval data."},\n'
            '  {"word": "dynamic", "explanation": "In computer science, dynamic refers to something that can change size or structure while a program is running."},\n'
            '  {"word": "interval", "explanation": "An interval is a range of values, usually between two endpoints."},\n'
            '  {"word": "queries", "explanation": "In computing, a query is a request for specific data or information from a system or database."}\n'
            "]"
        )

        MAX_TRIES = 5

        for _ in range(MAX_TRIES):
            try:
                result = call_openai_model(
                    model="gpt-4o",
                    system_prompt=system_prompt,
                    user_prompt=passage,
                    temperature=0.2,
                )
                print(result)

                res_dict = json.loads(result)
                break
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing JSON: {e}")
                result = "[]"
        else:
            return Response(
                {"error": "Failed to parse LLM response"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        passage_split_by_paragraphs = passage.split("\n")
        res = []
        for paragraph in passage_split_by_paragraphs:
            if paragraph.strip() == "":
                continue

            words_in_paragraph = [
                word.strip()
                for word in re.split(
                    r"([,\s\.\;\:\?\!\[\]\(\)\{\}\<\>\n\t]+)", paragraph
                )
                if word.strip() != ""
            ]
            i = 0
            paragraph_res = []
            while i < len(words_in_paragraph):
                found = False
                for item in res_dict:
                    word = item["word"]
                    explanation = item["explanation"]
                    word_split = word.split()
                    if (
                        i + len(word_split) <= len(words_in_paragraph)
                        and words_in_paragraph[i : i + len(word_split)] == word_split
                    ):
                        paragraph_res.append({"word": word, "explanation": explanation})
                        i += len(word_split)
                        found = True
                        break
                if not found:
                    paragraph_res.append({"word": words_in_paragraph[i]})
                    i += 1
            res.append(paragraph_res)

        return Response({"keywords_with_explanations": res}, status=status.HTTP_200_OK)
