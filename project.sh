#!/usr/bin/env bash

pip install -e .
pip install code2llm --upgrade
#code2llm ./ --streaming --strategy deep -o ./project
code2llm ./ -f toon -o ./

echo "🚀 Testing different output formats..."

# Test 1: Default TOON format
echo "📊 Test 1: Default TOON format"
source venv/bin/activate && python -m code2llm ./ -v -o ./project -m hybrid -f toon
python3 validate_toon.py output_toon/analysis.toon

# Test 2: All formats
rm -rf output_all/
echo "📊 Test 2: All formats (toon,yaml,json,mermaid,png)"
source venv/bin/activate && python -m code2llm ./ -v -o ./output_all -m hybrid -f all
ls -la output_all/

exit

# Test 3: TOON + YAML (for comparison)
echo "📊 Test 3: TOON + YAML (for validation)"
source venv/bin/activate && python -m code2llm ./ -v -o ./output_comparison -m hybrid -f toon,yaml
python3 validate_toon.py output_comparison/analysis.toon
python3 validate_toon.py output_comparison/analysis.yaml output_comparison/analysis.toon

# Test 4: Different analysis modes with TOON
echo "📊 Test 4: Different analysis modes with TOON"
source venv/bin/activate && python -m code2llm ./ -v -o ./output_modes -m hybrid -f toon
source venv/bin/activate && python -m code2llm ./ -v -o ./output_modes -m dynamic -f toon
source venv/bin/activate && python -m code2llm ./ -v -o ./output_modes -m behavioral -f toon
python3 validate_toon.py output_modes/analysis.toon

echo "✅ All tests completed!"
echo "📁 Check output directories:"
echo "  - output_toon/     (TOON only)"
echo "  - output_all/      (All formats)"
echo "  - output_comparison/ (TOON + YAML)"
echo "  - output_modes/    (Different modes)"