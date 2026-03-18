from django_celery_beat.models import CrontabSchedule, PeriodicTask

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Bootstrap the CorpTool Pinger Module'

    def handle(self, *args):
        self.stdout.write("Configuring Tasks!")
        schedule_bootstrap, _ = CrontabSchedule.objects.get_or_create(
            minute='*/10',
            hour='*',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='UTC'
        )

        PeriodicTask.objects.update_or_create(
            task='pinger.tasks.bootstrap_notification_tasks',
            defaults={
                'crontab': schedule_bootstrap,
                'name': 'CorpTools Pinger Bootstrap',
                'enabled': True
            }
        )

        self.stdout.write("Done!")
