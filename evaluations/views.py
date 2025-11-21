from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from .models import EvaluationCriteria, ProjectEvaluation
from projects.models import Project, TeamMember
import google.generativeai as genai
import json
import PyPDF2
import re

# Configure Gemini AI
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
except:
    pass  # Handle if API key not configured


# ============= EVALUATION CRITERIA MANAGEMENT =============

@login_required
def manage_criteria(request):
    """View all evaluation criteria"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('dashboard')

    faculty = request.user.faculty_profile
    criteria_list = EvaluationCriteria.objects.filter(faculty=faculty).order_by('-created_at')

    return render(request, 'evaluations/manage_criteria.html', {
        'criteria_list': criteria_list
    })


@login_required
def create_criteria(request):
    """Create new evaluation criteria"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        criteria_name = request.POST.get('criteria_name')
        criteria_description = request.POST.get('criteria_description')
        max_marks = request.POST.get('max_marks')

        faculty = request.user.faculty_profile

        try:
            EvaluationCriteria.objects.create(
                faculty=faculty,
                criteria_name=criteria_name,
                criteria_description=criteria_description,
                max_marks=int(max_marks)
            )
            messages.success(request, 'Evaluation criteria created successfully!')
            return redirect('manage_criteria')
        except Exception as e:
            messages.error(request, f'Error creating criteria: {str(e)}')

    return render(request, 'evaluations/create_criteria.html')


@login_required
def edit_criteria(request, criteria_id):
    """Edit evaluation criteria"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    faculty = request.user.faculty_profile
    criteria = get_object_or_404(EvaluationCriteria, id=criteria_id, faculty=faculty)

    if request.method == 'POST':
        criteria.criteria_name = request.POST.get('criteria_name')
        criteria.criteria_description = request.POST.get('criteria_description')
        criteria.max_marks = int(request.POST.get('max_marks'))
        criteria.save()

        messages.success(request, 'Criteria updated successfully!')
        return redirect('manage_criteria')

    return render(request, 'evaluations/edit_criteria.html', {'criteria': criteria})


@login_required
def delete_criteria(request, criteria_id):
    """Delete evaluation criteria"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    faculty = request.user.faculty_profile
    criteria = get_object_or_404(EvaluationCriteria, id=criteria_id, faculty=faculty)

    criteria_name = criteria.criteria_name
    criteria.delete()
    messages.success(request, f'Criteria "{criteria_name}" deleted successfully!')
    return redirect('manage_criteria')


# ============= PROJECT EVALUATION =============

@login_required
def evaluate_project(request, project_id):
    """Main evaluation page"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    faculty = request.user.faculty_profile
    project = get_object_or_404(Project, id=project_id, team__faculty=faculty)
    members = TeamMember.objects.filter(team=project.team).select_related('student')
    criteria_list = EvaluationCriteria.objects.filter(faculty=faculty)

    # Get or create evaluation
    evaluation = None
    try:
        evaluation = ProjectEvaluation.objects.get(project=project)
    except ProjectEvaluation.DoesNotExist:
        if criteria_list.exists():
            evaluation = ProjectEvaluation.objects.create(
                project=project,
                faculty=faculty,
                evaluation_criteria=json.dumps([{
                    'name': c.criteria_name,
                    'description': c.criteria_description,
                    'max_marks': int(c.max_marks)
                } for c in criteria_list])
            )

    context = {
        'project': project,
        'members': members,
        'criteria_list': criteria_list,
        'evaluation': evaluation,
    }

    return render(request, 'evaluations/evaluate_project.html', context)


@login_required
def ai_evaluate_project(request, project_id):
    """AI evaluation using Gemini"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method != 'POST':
        return redirect('evaluate_project', project_id=project_id)

    faculty = request.user.faculty_profile
    project = get_object_or_404(Project, id=project_id, team__faculty=faculty)
    criteria_list = EvaluationCriteria.objects.filter(faculty=faculty)

    if not criteria_list.exists():
        messages.error(request, 'Please create evaluation criteria first.')
        return redirect('evaluate_project', project_id=project_id)

    if not settings.GEMINI_API_KEY:
        messages.error(request, 'Gemini API key not configured. Please add it to .env file.')
        return redirect('evaluate_project', project_id=project_id)

    try:
        # Extract PDF text
        pdf_text = extract_pdf_text(project.project_report.path)

        # Prepare evaluation prompt
        criteria_text = "\n".join([
            f"- {c.criteria_name} ({c.max_marks} marks): {c.criteria_description}"
            for c in criteria_list
        ])

        total_marks = sum(c.max_marks for c in criteria_list)

        prompt = f"""You are an expert project evaluator. Evaluate this project and provide a concise, well-formatted evaluation.

PROJECT DETAILS:
- Project Name: {project.project_name}
- GitHub Link: {project.github_link}
- Team: {project.team.team_name}

PROJECT REPORT EXCERPT:
{pdf_text[:2500]}

EVALUATION CRITERIA:
{criteria_text}
Total Available: {total_marks} marks

INSTRUCTIONS:
1. Provide a total score out of {total_marks} marks
2. Give brief, clear feedback for each criterion
3. Keep your response concise and well-organized
4. Use bullet points for clarity

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

SCORE: [Your score out of {total_marks}]

EVALUATION SUMMARY:
[2-3 sentences summarizing the overall project quality]

DETAILED FEEDBACK:

1. {list(criteria_list)[0].criteria_name if criteria_list else 'Criterion 1'}:
   - [Brief evaluation point]
   - [Brief evaluation point]

2. {list(criteria_list)[1].criteria_name if len(criteria_list) > 1 else 'Criterion 2'}:
   - [Brief evaluation point]
   - [Brief evaluation point]

[Continue for each criterion]

STRENGTHS:
- [Key strength]
- [Key strength]

AREAS FOR IMPROVEMENT:
- [Improvement suggestion]
- [Improvement suggestion]

Keep each point concise (1 line). Total response should be clear and easy to read.
"""

        # Call Gemini AI
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        ai_response = response.text

        # Parse score
        marks = 0.0

        for line in ai_response.split('\n'):
            if 'SCORE:' in line.upper():
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    marks = float(numbers[0])
                    # Normalize to 100
                    marks = (marks / total_marks) * 100 if total_marks > 0 else 0.0
                break

        if marks == 0:
            marks = 75.0  # fallback

        formatted_feedback = format_ai_feedback(ai_response)

        # Get or create evaluation
        evaluation, created = ProjectEvaluation.objects.get_or_create(
            project=project,
            defaults={
                'faculty': faculty,
                'evaluation_criteria': json.dumps([{
                    'name': c.criteria_name,
                    'description': c.criteria_description,
                    'max_marks': int(c.max_marks)
                } for c in criteria_list])
            }
        )

        # Save as float - simple and clean
        evaluation.ai_marks = round(min(marks, 100.0), 2)
        evaluation.ai_feedback = formatted_feedback
        evaluation.ai_evaluated_at = timezone.now()
        evaluation.save()

        # Update project status if fully evaluated
        if evaluation.is_fully_evaluated:
            project.status = 'evaluated'
            project.save()

        messages.success(request, f'AI evaluation completed! Score: {evaluation.ai_marks}/100')

    except FileNotFoundError:
        messages.error(request, 'Project report file not found. Please re-upload the report.')
    except Exception as e:
        messages.error(request, f'AI evaluation failed: {str(e)}')
        print(f"AI Evaluation Error: {e}")
        import traceback
        traceback.print_exc()

    return redirect('evaluate_project', project_id=project_id)


@login_required
def faculty_evaluate_project(request, project_id):
    """Faculty manual evaluation"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method != 'POST':
        return redirect('evaluate_project', project_id=project_id)

    faculty = request.user.faculty_profile
    project = get_object_or_404(Project, id=project_id, team__faculty=faculty)

    faculty_marks = request.POST.get('faculty_marks')
    faculty_feedback = request.POST.get('faculty_feedback', '')

    try:
        criteria_list = EvaluationCriteria.objects.filter(faculty=faculty)

        # Get or create evaluation
        evaluation, created = ProjectEvaluation.objects.get_or_create(
            project=project,
            defaults={
                'faculty': faculty,
                'evaluation_criteria': json.dumps([{
                    'name': c.criteria_name,
                    'description': c.criteria_description,
                    'max_marks': int(c.max_marks)
                } for c in criteria_list])
            }
        )

        # Save as float - simple and clean
        evaluation.faculty_marks = float(faculty_marks)
        evaluation.faculty_feedback = faculty_feedback
        evaluation.faculty_evaluated_at = timezone.now()
        evaluation.save()

        # Update project status if fully evaluated
        if evaluation.is_fully_evaluated:
            project.status = 'evaluated'
            project.save()

        messages.success(request, 'Your evaluation has been saved successfully!')

    except ValueError:
        messages.error(request, 'Please enter valid marks (0-100)')
    except Exception as e:
        messages.error(request, f'Error saving evaluation: {str(e)}')
        print(f"Faculty Evaluation Error: {e}")
        import traceback
        traceback.print_exc()

    return redirect('evaluate_project', project_id=project_id)


@login_required
def evaluation_results(request, project_id):
    """View complete evaluation results"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    faculty = request.user.faculty_profile
    project = get_object_or_404(Project, id=project_id, team__faculty=faculty)

    try:
        evaluation = project.evaluation
    except ProjectEvaluation.DoesNotExist:
        messages.error(request, 'Project not evaluated yet.')
        return redirect('evaluate_project', project_id=project_id)

    context = {
        'project': project,
        'evaluation': evaluation,
    }

    return render(request, 'evaluations/evaluation_results.html', context)


# ============= HELPER FUNCTIONS =============

def extract_pdf_text(pdf_path):
    """Extract text from PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""

            # Extract first 5 pages (or all if less than 5)
            num_pages = min(5, len(pdf_reader.pages))

            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"

            if not text.strip():
                return "Unable to extract text from PDF. The file may be image-based or encrypted."

            return text

    except FileNotFoundError:
        return "Error: PDF file not found."
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


def format_ai_feedback(feedback_text):
    """Format AI feedback text to HTML with proper styling"""
    # Remove SCORE: line if present
    feedback_text = re.sub(r'SCORE:.*?\n', '', feedback_text, flags=re.IGNORECASE)

    lines = feedback_text.split('\n')
    formatted_html = []
    in_list = False

    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                formatted_html.append('</ul>')
                in_list = False
            continue

        # Convert **text** to <strong>text</strong>
        line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)

        # Convert *text* to <em>text</em>
        line = re.sub(r'\*(.*?)\*', r'<em>\1</em>', line)

        # Check if it's a heading (ALL CAPS or starts with #)
        if line.isupper() and len(line) > 3 and ':' in line:
            if in_list:
                formatted_html.append('</ul>')
                in_list = False
            formatted_html.append(f'<h4>{line.replace(":", "")}</h4>')

        # Check if it's a numbered item (1. , 2. , etc.)
        elif re.match(r'^\d+\.', line):
            if in_list:
                formatted_html.append('</ul>')
                in_list = False
            # Extract criterion name and content
            parts = line.split(':', 1)
            if len(parts) == 2:
                formatted_html.append(f'<div class="criteria-score"><strong>{parts[0]}:</strong> {parts[1]}</div>')
            else:
                formatted_html.append(f'<p><strong>{line}</strong></p>')

        # Check if it's a bullet point (-, *, •)
        elif line.startswith(('-', '•', '*')) or re.match(r'^\s*[-•*]', line):
            if not in_list:
                formatted_html.append('<ul>')
                in_list = True
            # Remove the bullet character
            content = re.sub(r'^\s*[-•*]\s*', '', line)
            formatted_html.append(f'<li>{content}</li>')

        # Regular paragraph
        else:
            if in_list:
                formatted_html.append('</ul>')
                in_list = False
            formatted_html.append(f'<p>{line}</p>')

    if in_list:
        formatted_html.append('</ul>')

    return '\n'.join(formatted_html)