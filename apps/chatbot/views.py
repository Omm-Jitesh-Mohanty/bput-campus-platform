# from django.shortcuts import render

# Create your views here.
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.core.permissions import require_any_perm, Perm
from .models import ChatSession, ChatMessage
from .rag import answer


@require_any_perm(Perm.USE_CHATBOT_STUDENT, Perm.USE_CHATBOT_ADMIN)
def chat_home(request):
    """Landing page: student or admin bot."""
    mode = 'admin' if request.user.is_admin_role() else 'student'
    sessions = ChatSession.objects.filter(user=request.user, mode=mode)[:10]
    return render(request, 'chatbot/home.html', {
        'mode': mode,
        'sessions': sessions,
    })


@login_required
@require_POST
def new_session(request):
    mode = 'admin' if request.user.is_admin_role() else 'student'
    session = ChatSession.objects.create(
        user=request.user, mode=mode,
        title='New conversation'
    )
    return redirect('chatbot:session', pk=session.id)


@login_required
def chat_session(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, user=request.user)
    return render(request, 'chatbot/session.html', {'session': session})


@login_required
@require_POST
def send_message(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, user=request.user)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_msg = payload.get('message', '').strip()
    if not user_msg:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Save user message
    ChatMessage.objects.create(session=session, role='user', content=user_msg)

    # Get history
    history = list(session.messages.values('role', 'content'))

    # RAG answer
    result = answer(
        query=user_msg,
        audience=session.mode,
        user=request.user,
        conversation_history=history,
    )

    # Save assistant message
    assistant = ChatMessage.objects.create(
        session=session,
        role='assistant',
        content=result['answer'],
        sources=result.get('sources', []),
        latency_ms=result.get('latency_ms', 0),
    )

    # Update session title if first
    if not session.title or session.title == 'New conversation':
        session.title = user_msg[:60]
        session.save(update_fields=['title', 'updated_at'])

    return JsonResponse({
        'ok': True,
        'reply': result['answer'],
        'sources': result.get('sources', []),
        'message_id': assistant.id,
        'latency_ms': result.get('latency_ms', 0),
        'source': result.get('source'),
    })


@login_required
@require_POST
def delete_session(request, pk):
    session = get_object_or_404(ChatSession, pk=pk, user=request.user)
    session.delete()
    return redirect('chatbot:home')