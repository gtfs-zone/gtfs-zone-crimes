import boto3
from moto import mock_aws

from gtfs_zone_crimes.pipeline.bucket import Bucket, BucketSettings


@mock_aws
def test_json_roundtrip():
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="crimes.gtfs.zone")
    bucket = Bucket(
        BucketSettings(
            endpoint="https://s3.amazonaws.com",
            bucket="crimes.gtfs.zone",
            access_key="x",
            secret_key="x",
            region="us-east-1",
        )
    )
    assert bucket.get_json("crimes.json") is None
    bucket.put_json("crimes.json", {"convictions": ["Lbo"]})
    assert bucket.get_json("crimes.json") == {"convictions": ["Lbo"]}
