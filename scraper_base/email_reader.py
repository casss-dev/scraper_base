import imaplib, email, enum
from email.utils import parsedate_to_datetime
from typing import Any, Generator
from dataclasses import dataclass
from datetime import datetime, timedelta


class Search:
    @staticmethod
    def on(day: Any) -> str:
        return f"ON {day.strftime('%d-%b-%Y')}"

    @staticmethod
    def subject(subject: str) -> str:
        return f'SUBJECT "{subject}"'

    @staticmethod
    def sent_since(day: Any) -> str:
        return f"SENTSINCE {day.strftime('%d-%b-%Y')}"

    @staticmethod
    def unseen() -> str:
        return "UNSEEN"

    @staticmethod
    def new() -> str:
        return "NEW"

    @staticmethod
    def all() -> str:
        return "ALL"

    @staticmethod
    def recent() -> str:
        return "RECENT"


class Flag(enum.Enum):
    """A flag indicating a mutation server-side"""

    SEEN = "\\Seen"
    """Message has been read"""
    DELETED = "\\Deleted"
    """Message is "deleted" for removal by later EXPUNGE"""


r"""
    \Answered   Message has been answered

    \Flagged    Message is "flagged" for urgent/special attention

    \Draft      Message has not completed composition (marked as a
                draft).
"""


class SearchCriteriaUnsupported(Exception):
    pass


class EmailProvider(enum.Enum):
    GMAIL = "imap.gmail.com"

    def raise_on_invalid(self, search: str):
        match self:
            case EmailProvider.GMAIL:
                if Search.recent() in search or Search.new() in search:
                    raise SearchCriteriaUnsupported(
                        f"A criteria in your search is unsupported by this email provider"
                    )


@dataclass
class EmailData:
    id: str
    to_addr: str
    from_addr: str
    subject: str
    date: str
    text: str
    html: str

    @property
    def date_obj(self) -> datetime:
        # format = "%a, %d %b %y %X %Z"
        # return datetime.datetime.strptime(self.date, format)
        return parsedate_to_datetime(self.date)

    @staticmethod
    def sort_by_newest(emails: list["EmailData"]):
        emails.sort(key=lambda e: e.date_obj.timestamp(), reverse=True)

    def __str__(self) -> str:
        return f"""
        ID: {self.id}
        FROM: {self.from_addr}
        TO: {self.to_addr}
        DATE: {self.date}
        SUBJECT: {self.subject}
        TEXT: {self.text}
        HTML: {self.html}
"""


class EmailReader:
    def __init__(
        self,
        address: str,
        password: str,
        mailbox: str = "INBOX",
        provider: EmailProvider = EmailProvider.GMAIL,
    ) -> None:
        self.address = address
        self.password = password
        self.mailbox = mailbox
        self.provider = provider

    def mark_read(self, email: EmailData):
        self.connection.store(email.id, "+FLAGS", Flag.SEEN.value)

    def mark_unread(self, email: EmailData):
        self.connection.store(email.id, "-FLAGS", Flag.SEEN.value)

    def search(self, *searches: str) -> Generator[EmailData, Any, Any]:
        """Searches for emails with the provided IMAP criteria

        Args:
            search (str): The criteria used to filter emails

        Returns:
            Generator[EmailData, Any, Any]: A list of emails matching the criteria
        """
        search = " ".join(searches)
        self.provider.raise_on_invalid(search)
        if not self.connection:
            return []
        _, ids = self.connection.search(None, search)
        for id in ids[0].split():
            _, data = self.connection.fetch(id, "(RFC822)")
            yield self.parse_email(id, data)

    def parse_email(self, id: str, data: Any) -> EmailData:
        msg = email.message_from_bytes(data[0][1])
        date = msg.get("Date", "")
        subject = msg.get("Subject", "")
        from_address = msg.get("From", "")
        to_address = msg.get("To", "")
        text = ""
        html = ""
        for part in msg.walk():
            match part.get_content_type():
                case "text/plain":
                    text += part.get_payload(decode=True).decode()
                case "text/html":
                    html += part.get_payload(decode=True).decode()
                case _:
                    continue
        return EmailData(id, to_address, from_address, subject, date, text, html)

    def __enter__(self) -> "EmailReader":
        self.connection = imaplib.IMAP4_SSL(self.provider.value)
        try:
            self.connection.login(self.address, self.password)
            self.connection.select(self.mailbox)
        except imaplib.IMAP4.error as e:
            raise e
        return self

    def __exit__(self, *args):
        if not self.connection:
            return
        self.connection.close()
        self.connection.logout()


def main():
    import os
    from itertools import islice
    from pprint import pprint

    address = os.environ["EMAIL_ADDR"]
    password = os.environ["EMAIL_PASS"]
    reader = EmailReader(address, password)
    with reader as mail:
        today = datetime.today()  # - timedelta(days=1)
        emails = list(islice(mail.search(Search.on(today)), 0, 3))
        EmailData.sort_by_newest(emails)
        pprint(emails)


if __name__ == "__main__":
    main()
