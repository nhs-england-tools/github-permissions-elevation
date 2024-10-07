resource "aws_dynamodb_table" "elevation_requests" {
  name         = "${terraform.workspace}_GithubElevationRequests"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user"
  range_key    = "requested_at"

  attribute {
    name = "user"
    type = "S"
  }

  attribute {
    name = "requested_at"
    type = "S"
  }
}
