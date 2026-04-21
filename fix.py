for f, pattern in [('app/auth.py', 'from sqlalchemy.orm import Session\n'), ('app/main.py', 'import logging\n')]:
    with open(f, 'r') as file:
        content = file.read()
    with open(f, 'w') as file:
        file.write(content.replace(pattern, ''))