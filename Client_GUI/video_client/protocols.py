import struct
from .logger import logger

class VideoInfo:
    def __init__(self, channel_id, segment_amount, segment_length, max_quality, author, title, description):
        self.channel_id = channel_id
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

            data = struct.pack('!IIBB',
                self.channel_id,
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

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return str((self.channel_id, self.author, self.segment_length, self.segment_amount, self.title, self.description, self.max_quality))

class ChannelInfo:
    def __init__(self, name, description, subscribers, owner, video_amount):
        self.name = name
        self.description = description
        self.subscribers = subscribers
        self.owner = owner
        self.video_amount = video_amount

    def to_bytes(self):
        name_bytes = self.name.encode('utf-8')
        desc_bytes = self.description.encode('utf-8')
        return (struct.pack('!I', len(name_bytes)) + name_bytes +
                struct.pack('!I', len(desc_bytes)) + desc_bytes +
                struct.pack('!III', self.subscribers, self.owner, self.video_amount))

class Protocol:
    """Protocol constants"""
    GET_VIDEO_INFO = 0x00
    GET_VIDEO_SEGMENT = 0x01
    GET_VIDEO_LIST = 0x02
    LOGIN = 0x03
    REGISTER = 0x04
    UPLOAD_VIDEO = 0x05
    DELETE_VIDEO = 0x06
    GET_CHANNEL_INFO = 0x07
    CREATE_CHANNEL = 0x08
    DELETE_CHANNEL = 0x09
    GET_CHANNEL_VIDEOS = 0x0A
    SUBSCRIBE = 0x0B
    UNSUBSCRIBE = 0x0C
    GET_USER_CHANNELS = 0x0D
    GET_USER_CHANNELS_BY_USER = 0x0E

    # Responses
    SUCCESS = 0x00
    FAILURE = 0x01
    INVALID_CREDENTIALS = 0x02
    USERNAME_TAKEN = 0x03
    CHANNEL_NAME_TAKEN = 0x04
    NOT_SUBSCRIBED = 0x05

    @staticmethod
    def command_to_str(cmd):
        commands = {
            0x00: 'GET_VIDEO_INFO',
            0x01: 'GET_VIDEO_SEGMENT',
            0x02: 'GET_VIDEO_LIST',
            0x03: 'LOGIN',
            0x04: 'REGISTER',
            0x05: 'UPLOAD_VIDEO',
            0x06: 'DELETE_VIDEO',
            0x07: 'GET_CHANNEL_INFO',
            0x08: 'CREATE_CHANNEL',
            0x09: 'DELETE_CHANNEL',
            0x0A: 'GET_CHANNEL_VIDEOS',
            0x0B: 'SUBSCRIBE',
            0x0C: 'UNSUBSCRIBE'
        }
        return commands.get(cmd, f'UNKNOWN_{cmd}')