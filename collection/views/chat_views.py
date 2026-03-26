import json
import os
import logging
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
import anthropic

from collection.chat_prompt import SYSTEM_PROMPT
from collection.chat_tools import TOOL_DEFINITIONS, execute_tool
from collection.models import (
    Caliber, Country, LoadType, BulletType, CaseType, PrimerType, PAColor,
)

logger = logging.getLogger(__name__)

# Maximum number of messages to send to the API (sliding window safety net)
MAX_HISTORY_MESSAGES = 40

# Maximum tool-call round-trips per user message (safety limit)
MAX_TOOL_ROUNDS = 5


def _log_chat_exchange(user, current_page, user_message, tool_calls, reply, error=None):
    """Log a chat exchange to a file for debugging and prompt tuning."""
    log_dir = getattr(settings, 'CHAT_LOG_DIR', None)
    if not log_dir:
        return

    try:
        os.makedirs(log_dir, exist_ok=True)
        # One file per day, named by date
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_path = os.path.join(log_dir, f'chat_{date_str}.log')

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"\n{'='*60}",
            f"[{timestamp}] User: {user} | Page: {current_page}",
            f"{'='*60}",
            f"USER: {user_message}",
        ]

        # Log each tool call round
        for i, tc in enumerate(tool_calls, 1):
            lines.append(f"\n--- Tool Call #{i}: {tc['name']} ---")
            lines.append(f"Input: {json.dumps(tc['input'], indent=2)}")
            lines.append(f"Result: {json.dumps(tc['result'], indent=2)}")

        if error:
            lines.append(f"\nERROR: {error}")
        else:
            lines.append(f"\nASSISTANT: {reply}")

        lines.append("")

        with open(log_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    except Exception as e:
        logger.warning(f"Failed to write chat log: {e}")


def _build_lookup_vocabulary(caliber_code):
    """Build a text summary of lookup table values for the system prompt."""
    sections = []

    # Countries for the current caliber
    countries = Country.objects.filter(
        caliber__code=caliber_code
    ).order_by('name')
    country_items = []
    for c in countries:
        if c.full_name and c.full_name != c.name:
            country_items.append(f'"{c.name}" ({c.full_name})')
        else:
            country_items.append(f'"{c.name}"')
    sections.append(f"Countries in this caliber: {', '.join(country_items)}")

    # Lookup tables (shared across calibers)
    for label, model in [
        ("Load Types", LoadType),
        ("Bullet Types", BulletType),
        ("Case Types", CaseType),
        ("Primer Types", PrimerType),
        ("PA (Primer Annulus) Colors", PAColor),
    ]:
        values = model.objects.all().order_by('display_name')
        items = [f'"{v.display_name}" (code: {v.value})' for v in values]
        sections.append(f"{label}: {', '.join(items)}")
    return '\n'.join(sections)


@login_required
@require_POST
def chat_message(request):
    """
    Chat endpoint that sends user messages to the Claude API.
    Handles tool calling with multi-turn round-trips.
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

    # Extract the current caliber code from the URL path (e.g., /9mmP/loads/42/ → 9mmP)
    current_caliber = ''
    if current_page:
        parts = current_page.strip('/').split('/')
        if parts and parts[0]:
            if Caliber.objects.filter(code=parts[0]).exists():
                current_caliber = parts[0]

    # Default to 9mmP when no caliber is in the URL (landing page, etc.)
    # This is appropriate for the primary collection; other deployments may want
    # a different default or to prompt the user.
    if not current_caliber:
        current_caliber = '9mmP'

    # Build lookup vocabulary so Claude knows the valid database values
    lookup_vocab = _build_lookup_vocabulary(current_caliber)

    # Build the system prompt with current page, caliber, and vocabulary context
    system = SYSTEM_PROMPT.format(
        current_page=current_page or 'unknown',
        current_caliber=current_caliber,
        lookup_vocabulary=lookup_vocab,
    )

    # Track tool calls for logging
    tool_call_log = []

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Tool-calling loop: Claude may request one or more tool calls
        # before giving a final text response
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system,
                messages=api_messages,
                tools=TOOL_DEFINITIONS,
            )

            # If Claude responds with just text, we're done
            if response.stop_reason == "end_of_turn":
                reply = _extract_text(response)
                break

            # If Claude wants to call tools, execute them and continue
            if response.stop_reason == "tool_use":
                # Add Claude's response (with tool_use blocks) to messages
                api_messages.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Execute each tool call and collect results
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = execute_tool(block.name, block.input)
                        tool_call_log.append({
                            "name": block.name,
                            "input": block.input,
                            "result": result,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })

                # Add tool results to messages for the next round
                api_messages.append({
                    "role": "user",
                    "content": tool_results,
                })
            else:
                # Unexpected stop reason — extract whatever text we have
                reply = _extract_text(response)
                break
        else:
            reply = "I'm sorry, I wasn't able to complete that request. Please try rephrasing your question."

        # Save only the user message and final text reply to session history
        # (tool call details are not persisted — they'd bloat the session)
        history.append({"role": "assistant", "content": reply})
        request.session['chat_history'] = history

        # Log the exchange
        _log_chat_exchange(
            user=request.user.username,
            current_page=current_page,
            user_message=user_message,
            tool_calls=tool_call_log,
            reply=reply,
        )

    except anthropic.AuthenticationError:
        _log_chat_exchange(request.user.username, current_page, user_message, tool_call_log, "", error="AuthenticationError")
        return JsonResponse({'error': 'Invalid API key.'}, status=500)
    except anthropic.RateLimitError:
        _log_chat_exchange(request.user.username, current_page, user_message, tool_call_log, "", error="RateLimitError")
        return JsonResponse({'error': 'Rate limit reached. Please wait a moment and try again.'}, status=429)
    except Exception as e:
        _log_chat_exchange(request.user.username, current_page, user_message, tool_call_log, "", error=str(e))
        return JsonResponse({'error': f'Something went wrong: {str(e)}'}, status=500)

    return JsonResponse({'reply': reply})


def _extract_text(response):
    """Extract text content from a Claude API response."""
    texts = [block.text for block in response.content if hasattr(block, 'text')]
    return "\n\n".join(texts) if texts else ""


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
