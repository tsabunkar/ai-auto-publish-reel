resource "aws_s3_bucket" "content" {
  bucket = "${var.content_bucket_name}-${var.environment}"
}

resource "aws_s3_bucket_versioning" "content" {
  bucket = aws_s3_bucket.content.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "content" {
  bucket = aws_s3_bucket.content.id

  rule {
    id     = "expire-prompts"
    status = "Enabled"
    filter {
      prefix = "prompts/"
    }
    expiration {
      days = 30
    }
  }

  rule {
    id     = "expire-audio"
    status = "Enabled"
    filter {
      prefix = "audio/"
    }
    expiration {
      days = 7
    }
  }

  rule {
    id     = "expire-videos"
    status = "Enabled"
    filter {
      prefix = "videos/"
    }
    expiration {
      days = 90
    }
  }
}

resource "aws_s3_bucket_public_access_block" "content" {
  bucket = aws_s3_bucket.content.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
