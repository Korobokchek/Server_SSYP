import struct
from .logger import logger

class VideoInfo:
    #создание переменных для хранения данных о видео и логирование этого
    def __init__(self, segment_amount, segment_length, max_quality, author, title, description):
        self.segment_amount = segment_amount
        self.segment_length = segment_length
        self.max_quality = max_quality
        self.author = author
        self.title = title
        self.description = description
        logger.debug(f"Created VideoInfo: {title} by {author}")

    @classmethod
    def from_bytes(cls, data):
        try:
            offset = 0
            segment_amount = struct.unpack_from('!I', data, offset)[0]
            offset += 4
            segment_length = struct.unpack_from('!B', data, offset)[0]
            offset += 1
            max_quality = struct.unpack_from('!B', data, offset)[0]
            offset += 1

            # Read author
            author_len = struct.unpack_from('!I', data, offset)[0]
            offset += 4
            author = data[offset:offset+author_len].decode('utf-8')
            offset += author_len

            # Read title
            title_len = struct.unpack_from('!I', data, offset)[0]
            offset += 4
            title = data[offset:offset+title_len].decode('utf-8')
            offset += title_len

            # Read description
            desc_len = struct.unpack_from('!I', data, offset)[0]
            offset += 4
            description = data[offset:offset+desc_len].decode('utf-8')

            return cls(segment_amount, segment_length, max_quality, author, title, description)
        except Exception as e:
            logger.error(f"Failed to parse VideoInfo: {str(e)}")
            raise

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

    @staticmethod
    def command_to_str(cmd):
        commands = {
            GET_INFO: 'GET_INFO',
            GET_CHUNK: 'GET_CHUNK',
            GET_LIST: 'GET_LIST',
            LOGIN: 'LOGIN',
            REGISTER: 'REGISTER',
            UPLOAD: 'UPLOAD'
        }
        return commands.get(cmd, 'UNKNOWN')