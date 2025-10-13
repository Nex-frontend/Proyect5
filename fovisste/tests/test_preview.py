from django.test import TestCase, Client
from django.contrib.auth.models import User, Permission
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from fovisste.models import Record
import json

class PreviewFlowTests(TestCase):
    def setUp(self):
        # Crear usuario con permiso para agregar registros
        self.user = User.objects.create_user('tester', password='pass')
        perm = Permission.objects.get(codename='add_record')
        self.user.user_permissions.add(perm)
        self.client = Client()
        self.client.force_login(self.user)
        # Configurar sesión con qna_ini y lote_anterior
        session = self.client.session
        session['qna_ini'] = '202510'
        session['lote_anterior'] = '0001'
        session.save()

    def make_fixed_width_line(self, rfc='RFC1234567890', nombre='Nombre de prueba'.ljust(30), tipo='A'):
        # Construir una línea con los campos mínimos según FIELDS en views
        # rfc(13), nombre(30), cadena1(37), tipo(1), impor(8), cpto(2), lote_actual(1), qna(6), ptje(2), observacio(47), lote_anterior(4), qna_ini(5)
        cadena1 = ''.ljust(37)
        impor = ''.ljust(8)
        cpto = ''.ljust(2)
        lote_actual = '1'
        qna = '202510'
        ptje = ''.ljust(2)
        observacio = ''.ljust(47)
        lote_anterior = '0001'
        qna_ini = '202510'
        line = f"{rfc[:13].ljust(13)}{nombre[:30].ljust(30)}{cadena1}{tipo}{impor}{cpto}{lote_actual}{qna}{ptje}{observacio}{lote_anterior}{qna_ini}"
        return line[:157]

    def test_preview_with_valid_file(self):
        content = (self.make_fixed_width_line(rfc='RFC0000000001', nombre='User One') + "\n" +
                   self.make_fixed_width_line(rfc='RFC0000000002', nombre='User Two'))
        f = SimpleUploadedFile('test.txt', content.encode('utf-8'))
        resp = self.client.post(reverse('api_preview'), {'files': [f]})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get('ok'))
        self.assertEqual(data.get('preview_count'), 2)
        # session debe contener preview_records
        session = self.client.session
        self.assertIn('preview_records', session)
        self.assertEqual(len(session['preview_records']), 2)

    def test_preview_with_empty_file(self):
        f = SimpleUploadedFile('empty.txt', b'\n\n')
        resp = self.client.post(reverse('api_preview'), {'files': [f]})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get('ok'))
        self.assertEqual(data.get('preview_count'), 0)
        # session no debe contener preview_records
        session = self.client.session
        self.assertNotIn('preview_records', session)

    def test_clear_preview_endpoint(self):
        # Primero crear preview en sesión manualmente
        session = self.client.session
        session['preview_records'] = [{'rfc':'X'}]
        session.save()
        resp = self.client.post(reverse('api_clear_preview'))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get('ok'))
        session = self.client.session
        self.assertNotIn('preview_records', session)

    def test_confirm_creates_records(self):
        # Preparar preview en sesión
        session = self.client.session
        session['preview_records'] = [
            {
                'rfc':'RFC0000000001',
                'nombre':'User One',
                'cadena1':'',
                'tipo':'A',
                'impor':'',
                'cpto':'',
                'lote_actual':'1',
                'qna':'202510',
                'ptje':'',
                'observacio':'',
                'lote_anterior':'0001',
                'qna_ini':'202510'
            }
        ]
        session.save()
        resp = self.client.post(reverse('api_upload'), {'confirm': '1'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get('ok'))
        # Comprobar que se creó el registro en BD
        self.assertEqual(Record.objects.filter(rfc='RFC0000000001').count(), 1)
        # Session debe haber sido limpiada del preview
        session = self.client.session
        self.assertNotIn('preview_records', session)
*** End Patch