"""
Prompts for converting informal student text → formal application.
"""


FORMATTER_SYSTEM = """You are an expert at writing formal applications in the
traditional Indian college letter format.

STRICT FORMAT — follow exactly:

To,
[Correct Designation],
[Institution / Office Name].

Subject: [One-line subject describing the purpose]

Respected Sir/Madam,

[Paragraph 1: Introduce the student using the verified name, roll number,
department, and batch. State the purpose of the application clearly.]

[Paragraph 2: Provide the relevant details from the student's input, such as
dates, reasons, amounts, locations, or other context.]

[Paragraph 3: A polite request for approval or necessary action, without
introducing any new facts.]

I shall be highly obliged for your kind consideration.

Thanking you,
Yours sincerely,

[Full Name]
Roll No.: [Roll Number]
[Department] · [Batch Year]
[Hostel Block, Room Number]

STRICT FACTUALITY RULES:
- Use ONLY information provided in the verified student details and the
  student's input.
- NEVER invent, assume, guess, or add facts.
- NEVER claim that the student has received permission, informed anyone,
  made arrangements, completed work, received approval, or taken any action
  unless the student explicitly stated it.
- NEVER add academic, medical, financial, family, administrative, or other
  circumstances that were not provided.
- Preserve names, dates, numbers, amounts, places, and stated reasons exactly.
- Do not calculate, reinterpret, or change durations from dates.
- If the student's stated duration and dates appear inconsistent, preserve
  the original information instead of correcting or inventing information.
- Translate informal language into formal language without changing its meaning.
- Do not remove important information supplied by the student.
- Do not add information merely to make the application sound more complete.

ADDRESS RULES:
- The "To" block must contain ONLY the authority/designation and the verified
  institution or office name.
- NEVER put the student's hostel block, room number, phone number, email,
  department, or roll number in the "To" block.
- Student hostel and room details belong only in the student's details/signature.
- NEVER use placeholders such as [Institution Name], [Department], or
  [Correct Designation] in the final answer.
- Use the verified institution name exactly as provided.

AUTHORITY RULES:
- leave / gatepass → The Hostel Warden
- document → The Academic Officer
- complaint → The Maintenance In-Charge
- fee issue → The Accounts Officer
- If the correct authority is supplied as verified context, use that value.

STYLE RULES:
- Use "Respected Sir/Madam," as the salutation.
- Keep the body approximately 100–150 words when enough information is
  available, but do not invent information just to reach the word count.
- Keep the language natural, respectful, concise, and suitable for an
  Indian college application.
- Do not use exaggerated or unnecessarily complex language.
- Do not add commentary, explanations, notes, markdown fences, or meta-text.
- Output ONLY the complete formal application.
"""


TEMPLATES = {
    'leave': (
        "Convert this into a formal LEAVE APPLICATION to the Hostel Warden / HOD.\n"
        "Student wrote: \"{raw}\"\n"
        "Formal application:"
    ),
    'gatepass': (
        "Convert this into a formal GATE PASS REQUEST to the Hostel Warden.\n"
        "Student wrote: \"{raw}\"\n"
        "Formal application:"
    ),
    'document': (
        "Convert this into a formal DOCUMENT / CERTIFICATE REQUEST to the Academic Office.\n"
        "Student wrote: \"{raw}\"\n"
        "Formal application:"
    ),
    'complaint': (
        "Convert this into a formal COMPLAINT to the Maintenance Department.\n"
        "Student wrote: \"{raw}\"\n"
        "Formal complaint:"
    ),
}


def build_formatter_prompt(raw_text, ticket_type):
    tpl = TEMPLATES.get(ticket_type, TEMPLATES['complaint'])
    return tpl.format(raw=raw_text.strip())


DESIGNATION_MAP = {
    'leave': 'The Hostel Warden',
    'gatepass': 'The Hostel Warden',
    'document': 'The Academic Officer',
    'complaint': 'The Maintenance In-Charge',
    'fee': 'The Accounts Officer',
}


def build_formatter_prompt_with_context(
    raw_text,
    ticket_type,
    student_ctx,
    extra_fields=None,
):
    designation = student_ctx.get(
        'designation',
        DESIGNATION_MAP.get(
            ticket_type,
            'The Concerned Authority',
        ),
    )

    institution_name = student_ctx.get(
        'institution_name',
        'BPUT Campus',
    )

    extra_lines = ''

    if extra_fields:
        filtered = {
            k: v
            for k, v in extra_fields.items()
            if v not in (None, '', [])
        }

        if filtered:
            extra_lines = (
                '\nAdditional verified details from the form:\n'
                + '\n'.join(
                    f"  - {k}: {v}"
                    for k, v in filtered.items()
                )
            )

    return f"""Write a formal {ticket_type} application in the traditional Indian
college format.

Student's informal text:
"{raw_text.strip()}"

VERIFIED DETAILS FROM COLLEGE RECORDS:
Use these values EXACTLY. Do not modify, replace, or invent them.

  - Institution Name: {institution_name}
  - Addressed To: {designation}
  - Student Name: {student_ctx.get('full_name', '')}
  - Roll Number: {student_ctx.get('username', '')}
  - Department: {student_ctx.get('department', '')}
  - Batch Year: {student_ctx.get('batch_year', '')}
  - Hostel Block: {student_ctx.get('hostel_block', '')}
  - Room Number: {student_ctx.get('room_number', '')}
  - Email: {student_ctx.get('email', '')}
  - Phone: {student_ctx.get('phone', '')}{extra_lines}

IMPORTANT:
- The student's informal text is the source of truth for the requested
  purpose, dates, reasons, and other facts.
- Do not invent facts that are not present in the student's text or verified
  details above.
- Do not claim that the student has taken permission, informed anyone,
  completed work, made arrangements, or received approval unless explicitly
  stated by the student.
- Preserve dates, numbers, amounts, names, and reasons exactly.
- Do not calculate or reinterpret the duration of leave or any other period.
- The "To" block must contain only the authority and institution/office.
- Do not put the student's hostel, room, phone, email, or department in the
  "To" block.
- Do not use placeholders such as [Institution Name].
- Output ONLY the complete formal application.

Write the formal application now.
"""


def fallback_formal_text(
    raw_text,
    ticket_type,
    student_name,
    department,
    batch_year,
    roll_number='',
    hostel='',
    room='',
    designation=None,
    institution_name='BPUT Campus',
):
    designation = designation or DESIGNATION_MAP.get(
        ticket_type,
        'The Concerned Authority',
    )

    type_labels = {
        'leave': 'Leave Application',
        'gatepass': 'Gate Pass Request',
        'document': 'Document Request',
        'complaint': 'Complaint',
        'fee': 'Fee Related Request',
    }

    subject = type_labels.get(
        ticket_type,
        f'{ticket_type.title()} Request',
    )

    return f"""To,
{designation},
{institution_name}.

Subject: {subject}

Respected Sir/Madam,

I, {student_name} (Roll No. {roll_number or student_name}), a student of
{department} Department, {batch_year} batch, wish to submit the following
request:

{raw_text.strip()}

I kindly request you to consider my application and take necessary action.

I shall be highly obliged for your kind consideration.

Thanking you,
Yours sincerely,

{student_name}
Roll No.: {roll_number or student_name}
{department} · {batch_year}
Hostel {hostel}, Room {room}
"""