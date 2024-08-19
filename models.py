from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=255)
    link = models.URLField(unique=True)
    summary = models.TextField()
    category = models.CharField(max_length=100)
    website = models.CharField(max_length=100)
    published = models.DateTimeField()
    image = models.URLField(default=None, null=True)


    def __str__(self):
        return self.title
