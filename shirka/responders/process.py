# vim: set fileencoding=utf-8 :
from shirka.responders import Responder, StreamResponse
from shirka.consumers import BaseTestCase
from shirka.tools import process
import paramiko, functools, re

class ProcessStreamResponse(StreamResponse):
    def __init__(self, proc, server, bot, paramiko):
        self.server = server
        self.proc = proc
        self.bot = bot
        self.paramiko = paramiko

    def handle(self, request, consumer):
        consumer.post("Starting process: %s@%s$ %s -\n%s#/process/%s" % (self.proc.user, self.proc.server, self.proc.command, self.bot.url, self.proc.id), request)

        try:
            client = self.paramiko.get_client(self.server['host'], self.server)
        except Exception, e:
            consumer.post("Error while getting paramiko client: %s" % e, request)
            return

        try:
            self.bot.process_executor.run(self.proc, functools.partial(process.paramiko_run, client))

            consumer.post("[OK] Process is completed: %s@%s$ %s -\n%s#/process/%s" % (self.proc.user, self.proc.server, self.proc.command, self.bot.url, self.proc.id), request)

        except paramiko.SSHException, e:
            consumer.post("[KO] An error occurs while executing the process: %s@%s$ %s -\n%s#/process/%s" % (self.proc.user, self.proc.server, self.proc.command, self.bot.url, self.proc.id), request)

        finally:
            client.close()


class ProcessResponder(Responder):
    def __init__(self, servers, users, commands, bot, paramiko):
        self.servers = servers
        self.users = users
        self.commands = commands
        self.bot = bot
        self.paramiko = paramiko

    def name(self):
        return "process"

    def generate(self, request):
        """
        usage: process server registered_command
        run a command on an remote server
        """
        if request.user.id not in self.users:
            return "You fool, you are not my master!!"

        words = request.content.split(" ")

        if len(words) < 3:
            return "Invalid command"

        if words[1] not in self.servers:
            return "Sorry, there is no such server (%s) available" % words[1]

        if words[2] not in self.commands:
            return "Sorry, the command keyword (%s) does not exist" % words[2]

        command = self.commands[words[2]]

        pos = 1

        for word in words[3:]:
            if re.search("[^0-9\.\-A-Za-z]", word):
                return "Invalid argument: %s for command: %s" % (word, command)

            command = command.replace("ARG%d" % pos, word)

            pos = pos + 1

        if re.search(r"ARG[0-9]", command):
            return "Sorry missing argument for command: %s" % command

        proc = process.Process(command)
        proc.server = words[1]
        proc.user = request.user.id

        return ProcessStreamResponse(proc, self.servers[words[1]].copy(), self.bot, self.paramiko)

class TestProcessResponder(BaseTestCase):
    def setUp(self):
        self.responder = ProcessResponder(
            { 'nono': {} },
            [1],
            { 'ls' : 'ls -ls'},
            None,
            None
        )

    def test_support(self):

        from shirka.consumers import Request, User

        request = Request("process nono ls", User('name', 'email@email.com', 1), "type", "test provider")
        response = self.responder.generate(request)

        self.assertIsInstance(response, ProcessStreamResponse)



