JOB_CREATE_STUDENT_USERS = "create_student_users"
JOB_CREATE_LEADS_FROM_EXCEL = "create_leads_from_excel"

JOB_SCHEDULES = [
    ("0 8 * * *", JOB_CREATE_STUDENT_USERS),
]
