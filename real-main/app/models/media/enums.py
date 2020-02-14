class MediaSize:
    NATIVE = 'native'
    K4 = '4K'
    P1080 = '1080p'
    P480 = '480p'
    P64 = '64p'

    _ALL = (NATIVE, K4, P1080, P480, P64)


class MediaStatus:
    AWAITING_UPLOAD = 'AWAITING_UPLOAD'
    UPLOADING = 'UPLOADING'
    PROCESSING_UPLOAD = 'PROCESSING_UPLOAD'
    UPLOADED = 'UPLOADED'
    ERROR = 'ERROR'
    ARCHIVED = 'ARCHIVED'
    DELETING = 'DELETING'

    _ALL = (AWAITING_UPLOAD, UPLOADING, PROCESSING_UPLOAD, UPLOADED, ERROR, ARCHIVED, DELETING)
