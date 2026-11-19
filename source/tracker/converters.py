"""URL path converter for MongoDB ObjectIds (24 hexadecimal characters)."""


class ObjectIdConverter:
    regex = "[0-9a-f]{24}"

    def to_python(self, value):
        return value  # Django's ObjectIdAutoField converts the string to bson.ObjectId

    def to_url(self, value):
        return str(value)
