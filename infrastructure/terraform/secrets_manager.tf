resource "aws_secretsmanager_secret" "instagram" {
  name                    = "instagram-credentials-${var.environment}"
  description             = "Instagram Graph API credentials for reel publishing"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "linkedin" {
  name                    = "linkedin-credentials-${var.environment}"
  description             = "LinkedIn API v2 credentials for video publishing"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "youtube" {
  name                    = "youtube-credentials-${var.environment}"
  description             = "YouTube Data API v3 credentials for video publishing"
  recovery_window_in_days = 7
}
