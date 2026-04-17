"""
pipeline/ai/prompts.py
======================

Prompt templates for EVUA's three AI-assist task types.

Each function takes the relevant source material and returns a complete
prompt string ready to send to the LLM client.

Design rules
------------
- Always end with "Output ONLY the [X], no explanation, no markdown fences."
  This keeps responses directly writable to files without post-processing.
- Keep prompts under ~2500 tokens to stay safely under free tier limits.
- Low temperature (set in client.py) + constrained output format = reliable results.
- Include the original AngularJS source so the model has full context.
"""

from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: Pipe transform() body completion
# ─────────────────────────────────────────────────────────────────────────────

def pipe_transform_prompt(
    pipe_name: str,
    filter_name: str,
    original_js_body: str,
    current_ts: str,
) -> str:
    """
    Prompt for completing a pipe's transform() method body.

    The engine generates pipe stubs with the original JS filter body
    commented out and transform() returning `value` unchanged.
    This prompt asks the model to port the JS logic to TypeScript.

    Parameters
    ----------
    pipe_name       : Angular class name e.g. 'CapitalizePipe'
    filter_name     : Original AngularJS filter name e.g. 'capitalize'
    original_js_body: The commented-out original JS (already extracted)
    current_ts      : The full current .pipe.ts file content
    """
    return f"""You are migrating an AngularJS filter to an Angular pipe.

AngularJS filter name: '{filter_name}'
Angular pipe class: '{pipe_name}'

Original AngularJS filter body:
{original_js_body}

Current Angular pipe file (transform() returns value unchanged — needs fixing):
{current_ts}

Your task: rewrite the complete pipe TypeScript file with a correct transform() implementation.
Port the AngularJS filter logic directly into transform().
- Replace `return value;` with the actual implementation
- Keep the @Pipe decorator and class structure identical
- Use TypeScript — no 'var', use proper parameter types where obvious
- The method signature must remain: transform(value: any, ...args: any[]): any

Output ONLY the complete TypeScript file content, no explanation, no markdown fences.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: Stub template completion
# ─────────────────────────────────────────────────────────────────────────────

def stub_template_prompt(
    component_name: str,
    controller_name: str,
    controller_js: str,
    component_ts: str,
    scope_properties: list[str],
    scope_methods: list[str],
) -> str:
    """
    Prompt for generating a real Angular template for a component that
    has only a stub template (no AngularJS template was found).

    Parameters
    ----------
    component_name   : Angular class name e.g. 'AuthComponent'
    controller_name  : Original AngularJS controller name
    controller_js    : The original AngularJS controller source code
    component_ts     : The generated Angular component TypeScript
    scope_properties : List of $scope property names from analysis
    scope_methods    : List of $scope method names from analysis
    """
    props_str   = ", ".join(scope_properties) if scope_properties else "none detected"
    methods_str = ", ".join(scope_methods)    if scope_methods    else "none detected"

    # Truncate controller JS to keep prompt under token limit
    if len(controller_js) > 1500:
        controller_js = controller_js[:1500] + "\n... (truncated)"

    return f"""You are migrating an AngularJS controller to an Angular component template.

Original AngularJS controller: {controller_name}
Angular component class: {component_name}

Component properties (from $scope): {props_str}
Component methods (from $scope): {methods_str}

Original AngularJS controller source:
{controller_js}

Generated Angular component TypeScript:
{component_ts}

Your task: write the Angular HTML template (.component.html) for this component.

Requirements:
- Use Angular template syntax: *ngIf, *ngFor, [(ngModel)], (click), [disabled], etc.
- Reference only properties and methods that exist in the component TypeScript above
- Include a form with inputs if the controller has login/save/create/submit methods
- Include a list with *ngFor if the controller loads a collection (users, products, items, etc.)
- Add [(ngModel)] on inputs that correspond to scope properties
- Keep it minimal but functional — 10 to 30 lines of HTML
- Do NOT use AngularJS syntax (ng-model, ng-repeat, ng-if, etc.)

Output ONLY the HTML template content, no explanation, no markdown fences, no TypeScript.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: Link function → ngAfterViewInit() migration
# ─────────────────────────────────────────────────────────────────────────────

def link_function_prompt(
    directive_name: str,
    component_name: str,
    link_fn_source: str,
    current_component_ts: str,
) -> str:
    """
    Prompt for migrating an AngularJS link() function into Angular's
    ngAfterViewInit() lifecycle hook.

    Parameters
    ----------
    directive_name       : Original AngularJS directive name e.g. 'userCard'
    component_name       : Angular class name e.g. 'UserCardComponent'
    link_fn_source       : Extracted source of the link() function body
    current_component_ts : The generated .component.ts file
    """
    # Truncate if needed
    if len(link_fn_source) > 1000:
        link_fn_source = link_fn_source[:1000] + "\n... (truncated)"

    return f"""You are migrating an AngularJS directive's link() function to Angular.

Original AngularJS directive: '{directive_name}'
Angular component class: '{component_name}'

Original link() function body:
{link_fn_source}

Current Angular component (has TODO comment where link logic should go):
{current_component_ts}

Your task: rewrite the complete Angular component TypeScript file with the link() logic
migrated into ngAfterViewInit().

Migration rules:
- Replace element[0] or elem[0] with this.el.nativeElement
- Replace element.on('click', fn) with @HostListener or direct DOM addEventListener
- Replace scope.$watch(...) with input property changes or RxJS if needed
- Replace attrs.xxx with @Input() properties
- Import ElementRef, AfterViewInit, HostListener from @angular/core as needed
- Add implements AfterViewInit to the class
- The constructor must have private el: ElementRef

Output ONLY the complete TypeScript file content, no explanation, no markdown fences.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Utility: strip markdown fences from model responses
# ─────────────────────────────────────────────────────────────────────────────

def clean_response(text: str, expected_type: str = "code") -> str:
    """
    Strip markdown code fences from model output.
    Models sometimes include ```typescript or ```html despite instructions.

    Parameters
    ----------
    text          : Raw model response
    expected_type : 'code' or 'html' — used to strip specific fence labels
    """
    import re
    # Strip ```typescript, ```ts, ```html, ```angular, ``` blocks
    text = re.sub(r"^```[a-z]*\n?", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text.strip(), flags=re.MULTILINE)
    return text.strip()