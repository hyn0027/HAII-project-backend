from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["POST"])
def summarize(request):
    passage = request.data.get("passage", "")
    # Fake summarization logic
    summary = "example_summary"
    return Response({"summary": summary, "input_length": len(passage)})
