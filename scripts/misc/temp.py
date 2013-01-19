class BaseList(list):
    """
    Abstract instance of a type specific list
    """
    def __init__(self, items = None):
        if items:
            for item in items:
                if self._is_valid(item):
                    self.append(item)

    def append(self, value):
        if self._is_valid(value):
            list.append(self, value)

    def __setitem__(self, index, value):
        if self._is_valid(value):
            list.__setitem__(self, index, value)

    def _is_valid(self, item):
        raise NotImplementedError('You should implement this')


class BaseObject(object):
    """
    Generic object used for test modeling
    """
    def __init__(self, **kwargs):
        axonlogger.info('Entering: BaseObject __init__')
        self.id = id(self)
        self.name = None

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                log.debug('Unrecognized attribute in BaseObject engine model FIXME: %s, for %r' % (key, self))
                #raise TypeError('Unrecognized attribute, %s, for ' % key, self)

    @property
    def version(self):
        return 1

    @property
    def is_valid(self):
        return True

    def __repr__(self):
        attrs = dict()
        for attr in dir(self):
            if attr.startswith('_'):
                continue

            if not callable(getattr(self, attr)):
                attrs[attr] = getattr(self, attr)

        return '%s: %s' % (type(self), attrs)

    def __str__(self):
        return self.name



###
# Protocol Tracks
###

class ProtocolTrack(BaseTrack, Protocol):
    def __init__(self, **kwargs):
        super(ProtocolTrack, self).__init__(**kwargs)

    @property
    def layer(self):
        return 7

    @property
    def server_port(self):
        return self._server_port


class StandardProtocolTrack(ProtocolTrack):
    ResponseDelay = enum('FIXED',
        'RANDOM')

    ResponseContent = enum('ASCII',
        'BINARY')

    ResponseSize = enum('FIXED',
        'RANDOM')

    def __init__(self, **kwargs):
        self.transactions_per_connection = 10

        # Server response size, in bytes
        self.response_size = 10000
        self.response_size_min = 100
        self.response_size_max = 100000
        self.response_size_type = StandardProtocolTrack.ResponseSize.FIXED

        # Server response delay, in milliseconds
        self.response_delay = 0
        self.response_delay_min = 1
        self.response_delay_max = 1000
        self.response_delay_type = StandardProtocolTrack.ResponseDelay.FIXED

        # Format of server response
        self.response_content_type = StandardProtocolTrack.ResponseContent.ASCII

        super(StandardProtocolTrack, self).__init__(**kwargs)

    @property
    def is_valid(self):
        # Check for valid response size/options
        if self.response_size_type == StandardProtocolTrack.ResponseSize.FIXED:
            if not isinstance(self.response_size, int):
                return False
            if self.response_size < 1:
                return False
        elif self.response_size_type == StandardProtocolTrack.ResponseSize.RANDOM:
            if not isinstance(self.response_size_min, int):
                return False
            if not isinstance(self.response_size_max, int):
                return False
            if self.response_size_min < 1:
                return False
            if self.response_size_max <= self.response_size_min:
                return False
        else:
            return False

        # Check for valid delay size/options
        if self.response_delay_type == StandardProtocolTrack.ResponseDelay.FIXED:
            if not isinstance(self.response_delay, int):
                return False
            if self.response_delay < 0:
                return False
        elif self.response_delay_type == StandardProtocolTrack.ResponseDelay.RANDOM:
            if not isinstance(self.response_delay_min, int):
                return False
            if not isinstance(self.response_delay_max, int):
                return False
            if self.response_delay_min < 0:
                return False
            if self.response_delay_max <= self.response_delay_min:
                return False
        else:
            return False

        if self.response_content_type not in StandardProtocolTrack.ResponseContent.reverse_mapping:
            return False

        return True


class HttpProtocolTrack(StandardProtocolTrack):
    Version = enum('HTTP_1_0',
        'HTTP_1_1')

    def __init__(self, **kwargs):
        self._server_port = 80
        self.http_version = HttpProtocolTrack.Version.HTTP_1_1
        super(HttpProtocolTrack, self).__init__(**kwargs)

    @property
    def protocol(self):
        return 'HTTP'

    @property
    def is_valid(self):
        if self.version not in HttpProtocolTrack.Version.reverse_mapping:
            return False

        return super(HttpProtocolTrack, self).is_valid


class FtpProtocolTrack(StandardProtocolTrack):
    Action = enum('GET',
        'PUT')

    def __init__(self, **kwargs):
        self._server_port = 21

        self.action = FtpProtocolTrack.Action.GET
        self.is_passive = False

        super(FtpProtocolTrack, self).__init__(**kwargs)

    @property
    def protocol(self):
        return 'FTP'

    @property
    def is_valid(self):
        if self.action not in FtpProtocolTrack.Action.reverse_mapping:
            return False

        if not isinstance(self.is_passive, bool):
            return False

        return super(FtpProtocolTrack, self).is_valid

