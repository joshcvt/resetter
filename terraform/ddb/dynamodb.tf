resource "aws_dynamodb_table" "resetter_game_status" {
  name           = "resetter-game-status"
  billing_mode   = "PROVISIONED"  # using this to keep us within the Free Tier
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "GameId"

  # You only define key and TTL attributes in TF.
  attribute {
    name = "GameId"
    type = "S"
  }

  # other attributes GameStatus etc will be inserted by the app

  ttl {
    attribute_name = "TTL"
    enabled        = true
  }

  tags = {
    Name = "resetter-game-status"
    App  = "resetter"
  }
}

output "resetter_game_status_arn" {
    value = aws_dynamodb_table.resetter_game_status.arn
}
