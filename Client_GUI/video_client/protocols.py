import struct
from .logger import logger

class VideoInfo:
    def __init__(self, segment_amount, segment_length, max_quality, author, title, description):
        self.segment_amount = segment_amount
        self.segment_length = segment_length
        self.max_quality = max_quality
        self.author = author
        self.title = title
        self.description = description
        logger.debug(f"Created VideoInfo: {title} by {author}")


    def to_bytes(self):
        try:
            author_bytes = self.author.encode('utf-8')
            title_bytes = self.title.encode('utf-8')
            description_bytes = self.description.encode('utf-8')

            data = struct.pack('!IBB',
                self.segment_amount,
                self.segment_length,
                self.max_quality)
            data += struct.pack('!I', len(author_bytes)) + author_bytes
            data += struct.pack('!I', len(title_bytes)) + title_bytes
            data += struct.pack('!I', len(description_bytes)) + description_bytes
            return data
        except Exception as e:
            logger.error(f"Failed to serialize VideoInfo: {str(e)}")
            raise

class Protocol:
    """Protocol constants"""
    GET_INFO = 0x00
    GET_CHUNK = 0x01
    GET_LIST = 0x02
    LOGIN = 0x03
    REGISTER = 0x04
    UPLOAD = 0x05
    GET_USER_VIDEOS = 0x06
    EDIT_VIDEO = 0x07

    # Login responses
    LOGIN_SUCCESS = 0x00
    LOGIN_NO_ACCOUNT = 0x01
    LOGIN_WRONG_PASSWORD = 0x02

    # Register responses
    REGISTER_SUCCESS = 0x00
    REGISTER_USERNAME_TAKEN = 0x01
    REGISTER_INVALID_CREDENTIALS = 0x02

    # Upload responses
    UPLOAD_PROGRESS = 0x00
    UPLOAD_FAILURE = 0x01
    UPLOAD_SUCCESS = 0x02

    @staticmethod
    def command_to_str(cmd):
        commands = {
            GET_INFO: 'GET_INFO',
            GET_CHUNK: 'GET_CHUNK',
            GET_LIST: 'GET_LIST',
            LOGIN: 'LOGIN',
            REGISTER: 'REGISTER',
            UPLOAD: 'UPLOAD',
            GET_USER_VIDEOS: 'GET_USER_VIDEOS',
            EDIT_VIDEO: 'EDIT_VIDEO'
        }
        return commands.get(cmd, 'UNKNOWN')