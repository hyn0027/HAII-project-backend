from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import random


class KeywordView(APIView):
    def post(self, request):
        passage = request.data.get("passage", "")
        if not passage:
            return Response(
                {"error": "No passage provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        passage_split_by_paragraphs = passage.split("\n")
        res = []
        for paragraph in passage_split_by_paragraphs:
            words = paragraph.split(" ")
            res_paragraph = []
            for word in words:
                if random.random() < 0.3:
                    res_paragraph.append(
                        {"word": word, "explanation": "example_explanation"}
                    )
                else:
                    res_paragraph.append({"word": word})
            res.append(res_paragraph)
        return Response({"keywords_with_expanations": res}, status=status.HTTP_200_OK)
