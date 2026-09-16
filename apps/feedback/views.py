# from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Feedback


@login_required
def submit_feedback(request):
    if request.user.is_admin_role():
        return redirect('dashboard:admin_home')

    if request.method == 'POST':
        category = request.POST.get('category')
        rating = request.POST.get('rating')
        comments = request.POST.get('comments', '').strip()
        is_anonymous = request.POST.get('is_anonymous') == 'on'

        if not category or not rating:
            messages.error(request, "Category and rating are required.")
        else:
            Feedback.objects.create(
                student=None if is_anonymous else request.user,
                category=category,
                rating=int(rating),
                comments=comments,
                is_anonymous=is_anonymous,
            )
            messages.success(request, "Thank you for your feedback!")
            return redirect('feedback:my_feedback')

    from apps.core.constants import FEEDBACK_CATEGORIES
    return render(request, 'feedback/submit.html', {
        'categories': FEEDBACK_CATEGORIES,
    })


@login_required
def my_feedback(request):
    if request.user.is_admin_role():
        return redirect('dashboard:admin_home')

    feedbacks = Feedback.objects.filter(student=request.user).order_by('-created_at')
    return render(request, 'feedback/my_list.html', {'feedbacks': feedbacks})