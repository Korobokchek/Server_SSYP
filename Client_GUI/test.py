import pytest
import struct
from video_client.protocols import VideoInfo


def pack_video_info(video):
    """Helper function to create test binary data"""
    author_bytes = video['author'].encode('utf-8')
    title_bytes = video['title'].encode('utf-8')
    desc_bytes = video['description'].encode('utf-8')

    data = struct.pack('!IBB',
                       video['segment_amount'],
                       video['segment_length'],
                       video['max_quality'])
    data += struct.pack('!I', len(author_bytes)) + author_bytes
    data += struct.pack('!I', len(title_bytes)) + title_bytes
    data += struct.pack('!I', len(desc_bytes)) + desc_bytes
    return data


TEST_CASES = [
    (
        {
            'segment_amount': 10,
            'segment_length': 15,
            'max_quality': 2,
            'author': "Test Author",
            'title': "Test Video",
            'description': "Short desc"
        },
        "Normal case"
    ),
    (
        {
            'segment_amount': 0,
            'segment_length': 1,
            'max_quality': 0,
            'author': "",
            'title': "",
            'description': ""
        },
        "Empty fields"
    ),
    (
        {
            'segment_amount': 255,
            'segment_length': 255,
            'max_quality': 255,
            'author': "A" * 100,
            'title': "B" * 100,
            'description': "C" * 1000
        },
        "Max field sizes"
    )
]


@pytest.mark.parametrize("video_data,test_name", TEST_CASES)
def test_from_bytes(video_data, test_name):
    """Test that from_bytes correctly unpacks data"""
    packed_data = pack_video_info(video_data)
    result = VideoInfo.from_bytes(packed_data)

    assert result['segment_amount'] == video_data['segment_amount']
    assert result['segment_length'] == video_data['segment_length']
    assert result['max_quality'] == video_data['max_quality']
    assert result['author'] == video_data['author']
    assert result['title'] == video_data['title']
    assert result['description'] == video_data['description']


def test_invalid_data():
    """Test handling of invalid/malformed data"""
    with pytest.raises(struct.error):
        VideoInfo.from_bytes(b'')  # Empty data

    with pytest.raises(struct.error):
        VideoInfo.from_bytes(b'invalid')  # Too short

    with pytest.raises(UnicodeDecodeError):
        # Corrupted string length
        bad_data = struct.pack('!IBB', 1, 1, 1) + struct.pack('!I', 10) + b'a' * 5
        VideoInfo.from_bytes(bad_data)