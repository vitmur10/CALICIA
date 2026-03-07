from enum import Enum


class VarsEnum(Enum):
    ADVERT = 'Реклама'
    LIMIT = 'Лимит бесплатных запросов'
    GOAL = 'Цель'


class ContentTypes(Enum):
    ANIMATION = 'animation'
    MESSAGE = 'message'
    PHOTO = 'photo'
    VIDEO = 'video'
