import logging
import unittest

from b2_config import (
    B2_USER_AGENT_EXTRA,
    get_b2_endpoint_url,
    load_b2_settings,
)

logging.disable(logging.CRITICAL)


def base_env():
    return {
        'B2_APPLICATION_KEY_ID': 'key-id',
        'B2_APPLICATION_KEY': 'application-key',
        'B2_BUCKET_NAME': 'single-bucket',
        'B2_REGION': 'us-west-004',
    }


class B2ConfigTests(unittest.TestCase):
    def test_loads_standard_b2_configuration(self):
        settings = load_b2_settings(base_env())

        self.assertEqual(settings.application_key_id, 'key-id')
        self.assertEqual(settings.application_key, 'application-key')
        self.assertEqual(settings.endpoint_url, 'https://s3.us-west-004.backblazeb2.com')
        self.assertEqual(settings.region_name, 'us-west-004')
        self.assertEqual(settings.input_bucket_name, 'single-bucket')
        self.assertEqual(settings.output_bucket_name, 'single-bucket')
        self.assertIn('(backblaze-b2-samples)', B2_USER_AGENT_EXTRA)

    def test_loads_legacy_configuration_for_rolling_deploys(self):
        settings = load_b2_settings({
            'AWS_ACCESS_KEY_ID': 'legacy-key-id',
            'AWS_SECRET_ACCESS_KEY': 'legacy-application-key',
            'AWS_ENDPOINT_URL': 'https://s3.us-west-004.backblazeb2.com',
            'BUCKET_NAME': 'legacy-bucket',
        })

        self.assertEqual(settings.application_key_id, 'legacy-key-id')
        self.assertEqual(settings.application_key, 'legacy-application-key')
        self.assertEqual(settings.endpoint_url, 'https://s3.us-west-004.backblazeb2.com')
        self.assertEqual(settings.region_name, 'us-west-004')
        self.assertEqual(settings.input_bucket_name, 'legacy-bucket')
        self.assertEqual(settings.output_bucket_name, 'legacy-bucket')

    def test_loads_distinct_input_and_output_buckets(self):
        env = base_env()
        env.update({
            'B2_INPUT_BUCKET_NAME': 'source-bucket',
            'B2_OUTPUT_BUCKET_NAME': 'zip-bucket',
        })

        settings = load_b2_settings(env)

        self.assertEqual(settings.input_bucket_name, 'source-bucket')
        self.assertEqual(settings.output_bucket_name, 'zip-bucket')

    def test_rejects_partial_dual_bucket_configuration(self):
        env = base_env()
        env['B2_INPUT_BUCKET_NAME'] = 'source-bucket'

        with self.assertRaises(SystemExit):
            load_b2_settings(env)

    def test_missing_required_b2_values_fail_closed(self):
        env = base_env()
        del env['B2_APPLICATION_KEY']

        with self.assertRaises(SystemExit):
            load_b2_settings(env)

    def test_region_safety_rejects_endpoint_injection(self):
        for bad_region in [
            '',
            'us-west-004/../evil',
            'a.b.c',
            '169.254.169.254',
            '-us-west-004',
            'us-west-004-',
        ]:
            with self.subTest(bad_region=bad_region):
                with self.assertRaises(SystemExit):
                    get_b2_endpoint_url(bad_region)

    def test_region_safety_allows_future_safe_labels(self):
        self.assertEqual(
            get_b2_endpoint_url('us-west-0001'),
            'https://s3.us-west-0001.backblazeb2.com',
        )
        self.assertEqual(
            get_b2_endpoint_url('region1'),
            'https://s3.region1.backblazeb2.com',
        )


if __name__ == '__main__':
    unittest.main()
