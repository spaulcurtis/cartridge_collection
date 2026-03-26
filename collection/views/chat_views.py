import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
import anthropic

from collection.chat_prompt import SYSTEM_PROMPT


# Maximum number of messages to send to the API (sliding window safety net)
MAX_HISTORY_MESSAGES = 40


@login_required
@require_POST
def chat_message(request):
    """
    Chat endpoint that sends user messages to the Claude API.
    Maintains conversation history in the Django session.
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        current_page = data.get('current_page', '')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    if not settings.ANTHROPIC_API_KEY:
        return JsonResponse({'error': 'Chat is not configured. API key is missing.'}, status=500)

    # Retrieve or initialize conversation history from session
    history = request.session.get('chat_history', [])

    # Add the new user message
    history.append({"role": "user", "content": user_message})

    # Apply sliding window to keep history manageable
    api_messages = history[-MAX_HISTORY_MESSAGES:]

    # Build the system prompt with current page context
    system = SYSTEM_PROMPT.format(current_page=current_page or 'unknown')

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=api_messages,
        )

        reply = response.content[0].text

        # Add assistant reply to history and save to session
        history.append({"role": "assistant", "content": reply})
        request.session['chat_history'] = history

    except anthropic.AuthenticationError:
        return JsonResponse({'error': 'Invalid API key.'}, status=500)
    except anthropic.RateLimitError:
        return JsonResponse({'error': 'Rate limit reached. Please wait a moment and try again.'}, status=429)
    except Exception as e:
        return JsonResponse({'error': f'Something went wrong: {str(e)}'}, status=500)

    return JsonResponse({'reply': reply})


@login_required
def chat_history(request):
    """Return the conversation history from the session."""
    history = request.session.get('chat_history', [])
    return JsonResponse({'messages': history})


@login_required
@require_POST
def chat_clear(request):
    """Clear the conversation history."""
    request.session.pop('chat_history', None)
    return JsonResponse({'status': 'ok'})
