from django.core.management.commands.runserver import Command as runserver

runserver.default_port = '1337'
runserver.default_addr = '0.0.0.0'
