from django import db, forms
from django.contrib import admin
from django.core import urlresolvers
from django.utils.safestring import mark_safe

from gobotany.plantshare import models


class _Base(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('/static/admin/admin_gb.css',)
        }
        js = ('/static/admin/admin_gb.js',)


class QuestionAdminForm(forms.ModelForm):
    question = forms.CharField(
        widget=forms.Textarea(attrs={'rows':3, 'cols':80})
    )
    answer = forms.CharField(
        widget=forms.Textarea(attrs={'rows':7, 'cols':80})
    )
    class Meta:
        model = models.Question
        exclude = {}


class QuestionAdmin(_Base):
    date_hierarchy = 'asked'
    fields = ('question', 'image_links', 'asked_by', 'answer', 'approved')
    form = QuestionAdminForm
    list_display = ('question', 'answer', 'asked', 'approved', 'id')
    list_filter = ('approved', 'answered', 'asked')
    ordering = ['-answered']
    readonly_fields = ['image_links', 'asked_by']
    search_fields = ['question', 'answer']

    def image_links(self, obj):
        """Present images as thumbnails linked to the larger versions,
        for viewing when answering a question.
        """
        html = ''
        images = obj.images.all()
        if images:
            for image in images:
                html += '<a href="%s"><img src="%s"></a> ' % (
                    image.image.url, image.thumb.url)
            return html
        else:
            return None
    image_links.short_description = 'Images'
    image_links.allow_tags = True


class LocationAdmin(_Base):
    pass


class SightingAdmin(_Base):
    fields = ('user', 'created', 'identification', 'notes', 'location_link',
        'location_notes', 'photographs', 'visibility', 'flagged',
        'approved', 'email')
    readonly_fields = ('user', 'location_link', 'photographs', 'email',)
    formfield_overrides = {
        db.models.TextField:
            {'widget': forms.Textarea(attrs={'rows': 3, 'cols': 80})},
    }
    list_display = ('identification', 'location', 'display_name', 'pics',
        'email', 'created', 'visibility', 'flagged', 'approved')
    list_filter = ('created', 'visibility', 'flagged', 'approved')
    search_fields = ('identification', 'location__city', 'location__state',)

    def location_link(self, obj):
        change_url = urlresolvers.reverse('admin:plantshare_location_change',
            args=(obj.location.id,))
        return mark_safe('<a href="%s">%s</a>' % (change_url,
            obj.location.user_input))
    location_link.short_description = 'Location'

    def display_name(self, obj):
        display_name = ''
        try:
            profile = models.UserProfile.objects.get(user=obj.user)
            display_name = profile.user_display_name()
        except models.UserProfile.DoesNotExist:
            display_name = obj.user.username
        return display_name
    display_name.short_description = 'User'

    def email(self, obj):
        email_address = obj.user.email or ''
        return email_address

    def pics(self, obj):
        return len(obj.private_photos())

    def photographs(self, obj):
        html = ''
        for photo in obj.private_photos():
            html += '<a href="%s"><img src="%s"></a> ' % (photo.image.url,
                photo.thumb.url)
        return html
    photographs.short_description = 'Photos'
    photographs.allow_tags = True

class ScreenedImageAdmin(_Base):
    list_display = ('image_type', 'uploaded', 'uploaded_by',
        'email', 'screened', 'screened_by', 'is_approved', 'admin_thumb')
    list_filter = ('is_approved',)
    list_editable = ('is_approved',)

    def email(self, obj):
        return obj.uploaded_by.email

    def admin_thumb(self, obj):
        """Show thumbnails. Doing this, because ImageKit's AdminThumbnail
        would not render."""
        return '<img src="%s">' % (obj.thumb.url)
    admin_thumb.short_description = 'Thumbnail'
    admin_thumb.allow_tags = True


admin.site.register(models.Question, QuestionAdmin)
admin.site.register(models.Location, LocationAdmin)
admin.site.register(models.Sighting, SightingAdmin)
admin.site.register(models.ScreenedImage, ScreenedImageAdmin)
