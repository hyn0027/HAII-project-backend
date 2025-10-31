from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class SummarizeView(APIView):
    def post(self, request):
        passage = request.data.get("passage", "")
        if not passage:
            return Response(
                {"error": "No passage provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Fake summarization (you'll replace this with actual logic later)
        summary = "example_summary"
        return Response({"summary": summary}, status=status.HTTP_200_OK)
