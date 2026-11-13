"""Released member/pattern/error-alias rulings, using sealed corpus sources."""
from pathlib import Path
from string_rows import row

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    ('nullary-let', 'typecheck/nullary_arm_let_assign.lu', 'E0410'),
    ('nullary-var', 'typecheck/nullary_arm_var_assign.lu', ''),
    ('variant-twice', 'resolve/enum_variant_twice.lu', 'E0302'),
    ('variant-payload-twice', 'resolve/enum_variant_twice_payload.lu', 'E0302'),
    ('field-twice', 'resolve/struct_field_twice.lu', 'E0302'),
    ('or-binds', 'typecheck/or_pattern_binds.lu', ''),
    ('or-missing', 'typecheck/or_pattern_binds_missing.lu', 'E0828'),
    ('or-types', 'typecheck/or_pattern_binds_types.lu', 'E0401'),
    ('or-product', 'grammar/match_arm_or_over_product.lu', ''),
    ('name-twice-struct', 'typecheck/pattern_name_twice_struct.lu', 'E0827'),
    ('name-twice-types', 'typecheck/pattern_name_twice_types.lu', 'E0827'),
    ('name-twice-let', 'typecheck/pattern_name_twice_let.lu', 'E0827'),
    ('name-twice-at', 'typecheck/pattern_name_twice_at.lu', 'E0827'),
    ('name-twice-nested', 'typecheck/pattern_name_twice_nested.lu', 'E0827'),
    ('name-twice-for', 'typecheck/pattern_name_twice_for.lu', 'E0827'),
    ('param-twice', 'typecheck/param_name_twice.lu', 'E0827'),
    ('rec-enum', 'typecheck/rec_by_value_enum.lu', 'E0404'),
    ('rec-tuple', 'typecheck/rec_by_value_tuple.lu', 'E0404'),
    ('rec-mutual', 'typecheck/rec_by_value_mutual.lu', 'E0404'),
    ('rec-unused', 'typecheck/rec_by_value_unused.lu', 'E0404'),
    ('match-immutable', 'typecheck/match_binding_assign.lu', 'E0410'),
    ('for-immutable', 'typecheck/for_binding_assign.lu', 'E0410'),
    ('else-immutable', 'typecheck/else_binding_assign.lu', 'E0410'),
    ('match-shadow-var', 'typecheck/match_binding_var_shadow.lu', ''),
    ('alias-cycle-unused', 'rows/negative/error_alias_cycle_unused.lu', 'E0610'),
    ('alias-cycle-pair-unused', 'rows/negative/error_alias_cycle_pair_unused.lu', 'E0610'),
    ('alias-union-own-after', 'rows/error_alias_union_own_after.lu', ''),
    ('alias-union-own-conflict', 'rows/negative/error_alias_union_own_after_payload.lu', 'E0609'),
    ('own-tags-twice', 'rows/negative/dup_tags.lu', 'E0601'),
    ('variant-tests-twice', 'typecheck/pattern_variant_tests_twice.lu', ''),
]
AT = {
    'nullary-let': '19:19', 'variant-twice': '10:13', 'variant-payload-twice': '9:18',
    'field-twice': '11:5', 'or-missing': '14:16', 'or-types': '14:18',
    'name-twice-struct': '13:22', 'name-twice-types': '13:22',
    'name-twice-let': '9:13', 'name-twice-at': '10:13', 'name-twice-nested': '10:17',
    'name-twice-for': '10:13', 'param-twice': '8:14',
    'rec-enum': '11:15', 'rec-tuple': '8:15', 'rec-mutual': '10:20', 'rec-unused': '8:20',
    'match-immutable': '15:13', 'for-immutable': '11:9', 'else-immutable': '12:9',
    'alias-cycle-unused': '11:12', 'alias-cycle-pair-unused': '12:12',
    'alias-union-own-conflict': '12:29', 'own-tags-twice': '9:28',
}
ROWS = [row(name, (ROOT / '.wolf-bin/reference/corpus' / path).read_text().rstrip('\n'), code, AT.get(name))
        for name, path, code in CASES]
