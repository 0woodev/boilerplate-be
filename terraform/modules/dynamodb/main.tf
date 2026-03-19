locals {
  default_tags = merge({
    Project = var.project_name
    Stage   = var.stage
  }, var.tags)

  # 테이블별 attribute 목록 (중복 제거): hash_key + range_key + GSI keys + LSI keys
  all_attributes = {
    for tname, t in var.tables : tname => distinct(concat(
      [{ name = t.hash_key, type = t.hash_key_type }],
      t.range_key != null ? [{ name = t.range_key, type = t.range_key_type }] : [],
      flatten([for g in t.gsi : concat(
        [{ name = g.hash_key, type = g.hash_key_type }],
        g.range_key != null ? [{ name = g.range_key, type = g.range_key_type }] : []
      )]),
      flatten([for l in t.lsi : [
        { name = l.range_key, type = l.range_key_type }
      ]])
    ))
  }
}

resource "aws_dynamodb_table" "this" {
  for_each = var.tables

  name         = "${var.project_name}-${var.stage}-${each.key}"
  billing_mode = each.value.billing_mode
  hash_key     = each.value.hash_key
  range_key    = each.value.range_key

  read_capacity  = each.value.billing_mode == "PROVISIONED" ? each.value.read_capacity : null
  write_capacity = each.value.billing_mode == "PROVISIONED" ? each.value.write_capacity : null

  # 키 attribute 선언 (중복 없이)
  dynamic "attribute" {
    for_each = local.all_attributes[each.key]
    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }

  # TTL
  dynamic "ttl" {
    for_each = each.value.ttl_attribute != null ? [1] : []
    content {
      attribute_name = each.value.ttl_attribute
      enabled        = true
    }
  }

  # 스트림
  stream_enabled   = each.value.stream_enabled
  stream_view_type = each.value.stream_enabled ? each.value.stream_view_type : null

  # PITR
  point_in_time_recovery {
    enabled = each.value.point_in_time_recovery
  }

  # 암호화
  dynamic "server_side_encryption" {
    for_each = each.value.server_side_encryption ? [1] : []
    content {
      enabled     = true
      kms_key_arn = each.value.kms_master_key_id
    }
  }

  # GSI
  dynamic "global_secondary_index" {
    for_each = { for g in each.value.gsi : g.name => g }
    content {
      name               = global_secondary_index.value.name
      hash_key           = global_secondary_index.value.hash_key
      range_key          = global_secondary_index.value.range_key
      projection_type    = global_secondary_index.value.projection_type
      non_key_attributes = global_secondary_index.value.projection_type == "INCLUDE" ? global_secondary_index.value.non_key_attributes : null
      read_capacity      = each.value.billing_mode == "PROVISIONED" ? global_secondary_index.value.read_capacity : null
      write_capacity     = each.value.billing_mode == "PROVISIONED" ? global_secondary_index.value.write_capacity : null
    }
  }

  # LSI
  dynamic "local_secondary_index" {
    for_each = { for l in each.value.lsi : l.name => l }
    content {
      name               = local_secondary_index.value.name
      range_key          = local_secondary_index.value.range_key
      projection_type    = local_secondary_index.value.projection_type
      non_key_attributes = local_secondary_index.value.projection_type == "INCLUDE" ? local_secondary_index.value.non_key_attributes : null
    }
  }

  tags = merge(local.default_tags, each.value.tags)

  lifecycle {
    # 실수로 인한 테이블 삭제 방지. 삭제가 필요하면 이 블록을 주석 처리 후 apply
    prevent_destroy = true
  }
}
