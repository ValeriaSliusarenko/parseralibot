from aioimaplib import aioimaplib
from iop.core.message import Message
import asyncio
import email
import email.header
import email.utils


class MailBox:
    def __init__(self, user: str, password: str, server: str):
        self.user = user
        self.password = password
        self.server = server
        self.__client = None
        self.__last_seen = '0'
        self.__queue = []

    async def __connection(self):
        if self.__client is None:
            client = aioimaplib.IMAP4_SSL(self.server)
            await client.wait_hello_from_server()
            await client.login(self.user, self.password)
            res, _ = await client.select()
            assert res == 'OK'
            self.__client = client
        try:
            await self.__client.noop()
        except Exception as ex:
            self.__client = None
            return await self.__connection()

        return self.__client

    async def __get_unseen_uid(self):
        if len(self.__queue) != 0:
            item = self.__queue.pop()
            return item
        offset = str(int(self.__last_seen) + 1)
        res, data = await (await self.__connection()).uid_search('UNSEEN', f'UID {offset}:*')
        assert res == 'OK'
        if data[0] != '':
            uids = list(map(str, sorted(map(int, data[0].split()), reverse=True)))
            if uids[-1] == self.__last_seen:
                return None
            self.__queue = uids
            return await self.__get_unseen_uid()
        return None

    def __decode_addr(self, content):
        partA, value = email.utils.parseaddr(content)
        return self.__decode_content(partA), value

    def __decode_content(self, content):
        partA, encoder = email.header.decode_header(content)[0]
        if isinstance(partA, bytes):
            partA = partA.decode(encoder)
        return partA

    async def __fetch(self, uid):
        res, msg = await (await self.__connection()).uid('FETCH', str(uid), 'BODY.PEEK[HEADER]')
        assert res == 'OK'
        mail = email.message_from_bytes(msg[1])
        subject = self.__decode_content(mail['subject'])
        rname, sender = self.__decode_addr(mail['from'])
        name, receiver = self.__decode_addr(mail['to'])
        self.__last_seen = uid
        return Message(payload=subject, msgid=str(uid), to=receiver, sender_name=rname, sender=sender)

    async def unseen(self, poll_interval: int = 5):
        while True:
            uid = await self.__get_unseen_uid()
            if uid is None:
                await asyncio.sleep(poll_interval)
                continue
            return await self.__fetch(uid)
