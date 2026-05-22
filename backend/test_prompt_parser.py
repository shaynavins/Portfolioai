#!/usr/bin/env python3
"""
Test script for the advanced prompt parser.
Validates parsing of design intent and portfolio specifications.
"""
import sys
sys.path.insert(0, '/Users/shaynavinoth/Downloads/portfolioai/backend')

from api.integrations.prompt_parser import parse_user_prompt
import json

# Test prompts
test_prompts = [
    {
        "name": "Full featured portfolio",
        "prompt": "Agentic AI Developer at BITS. Own a club called Lynq startup founder. Student. I want my design to have a brown girl emoji avatar with curly hair which is dynamic to cursor movement. The background should be interactive and fun. All my github projects should be shown. I want a bold, creative design with spacious layout and vibrant colors.",
    },
    {
        "name": "Minimal professional",
        "prompt": "Senior Software Engineer at Google. Focus on clean, minimal design. Professional corporate look.",
    },
    {
        "name": "Creative designer",
        "prompt": "Product Designer & Creative Developer. Founder of DesignCo startup. I want an artistic, playful portfolio with lots of animation and colorful gradients. Display all projects in a grid layout.",
    },
]

def test_parser():
    print("Testing Advanced Portfolio Prompt Parser\n" + "=" * 60)
    
    for test in test_prompts:
        print(f"\nTest: {test['name']}")
        print("-" * 60)
        print(f"Prompt: {test['prompt'][:80]}...")
        
        spec = parse_user_prompt(test['prompt'], "")
        
        print(f"\n✓ Parsed Bio: {spec.bio}")
        print(f"✓ Tagline: {spec.tagline}")
        print(f"✓ Highlights: {spec.highlights}")
        print(f"✓ Design Emoji: {spec.design_emoji}")
        print(f"✓ Interactive BG: {spec.interactive_bg}")
        print(f"✓ Show All Projects: {spec.show_all_projects}")
        print(f"✓ CTA Text: {spec.cta_text}")
        
        print(f"\nDesign Config:")
        print(f"  - Color Mood: {spec.design_config.color_mood}")
        print(f"  - Layout: {spec.design_config.layout}")
        print(f"  - Background: {spec.design_config.background}")
        print(f"  - Animation Level: {spec.design_config.animation_level}")
        print(f"  - Typography: {spec.design_config.typography}")
        print(f"  - Spacing: {spec.design_config.spacing}")
        print(f"  - Avatar Motion: {spec.design_config.avatar_motion}")
        print(f"  - Project Style: {spec.design_config.project_style}")
        print(f"  - Sections: {spec.design_config.sections}")
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")

if __name__ == "__main__":
    test_parser()
