# build a poc to autograde math assessments using gpt-4 and tts-1 models
# the workflow would be as follows:
# 1. student submit answers to all questions
# 2. grader grades the questions
# 3. grader provides feedback to the student
# 4. tts model generates audio feedback

import streamlit as st
from openai import OpenAI
from math import floor
from pathlib import Path
import xml.etree.ElementTree as ET
import html
import re

client = OpenAI()


@st.cache_data()
def generate_feedback_image(problem_statement:str,solution:dict, answer:str, image_url:str, teacher_notes:str):
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        temperature=0,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": f"""
                 #context#: i am a math teacher for the fifth grade and i'd like to provide feedback to a student on a math problem.
                 #objective#: provide specific and effective feedback 
                 #tone#: either point to the right direction or ask guiding questions.
                 #audience#: fifth grade student in the US.
                 #problem statement#: {problem_statement}
                 #solution#: {solution}
                 #answer#: {answer}
                 #teacher notes#: {teacher_notes}
                
                 #response#:
                 """},
                {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                },
                },
            ],
            }
        ],
        max_tokens=1000, # careful with this 
        )

    return response.choices[0].message.content

@st.cache_data()
def analyze_multiple_select_image(problem_statement:str,solution:dict, answer:str, image_url:str, teacher_notes:str,
                                            skills_tested:str):
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        temperature=0,
        messages=[
            {
            "role": "user",
            "content": [
                {"type": "text", "text": f"""
                 <context>: analyze the student's response to a multiple select math problem containing images.
                 you are provided with problem statement in <problem statement> tag
                 , solution in <solution> tag, student's answer in <answer> tag,  optional teacher's note in <teacher notes> tag, as well as the skills being assessed for the question in <skills assessed> tag. 
                 please analyze the student's response. 
                 <objective>: understand student's thought process and weaknesses. 
                 <problem statement>: {problem_statement} </problem statement>
                 <solution>: {solution} </solution>
                 <answer>: {answer} </answer>
                 <teacher notes>: {teacher_notes} </teacher notes>
                 <skills assessed>: {skills_tested} </skills assessed>
                 <analysis>: provide detailed analysis to understand the student's thought process and weaknesses.
                 """},
                {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                },
                },
            ],
            }
        ],
        max_tokens=1000, # careful with this 
        )

    return response.choices[0].message.content
@st.cache_data()
def analyze_multiple_select(problem_statement:str,solution:dict, answer:str, teacher_notes:str,
                            skills_tested:str):
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        temperature=0,
        messages=[
             {"role": "system", 
             "content": 'you analyze the student\'s response to a multiple select math problem'},
             {"role": "user",
            "content":  f"""
                 #context#: analyze the student's response to a multiple select math problem.
                 you are provided with problem statement, solution, student's answer,  optional teacher's note, as well as the skills being assessed for the question. 
                 please analyze the student's response. 
                 #objective#: understand student's thought process and weaknesses. 
                 #problem statement#: {problem_statement}
                 #solution#: {solution}
                 #answer#: {answer}
                 #teacher notes#: {teacher_notes}
                 #skills assessed#: {skills_tested}
                 #analysis#: provide detailed analysis to understand the student's thought process and weaknesses.
                 """},
            ],
        max_tokens=1000, # careful with this 
        )

    return response.choices[0].message.content
# 1. compare the student's answer to the solution. 
#                  2. point out what went wrong.
#                  3. evaluate the student's understanding of the skills tested {skills_tested}
#                  4. provide a hint to guide the student to the right answer but never reveal the answer directly.
@st.cache_data()
def generate_feedback_short_response_image(problem_statement:str,solution:dict, answer:str, image_url:str, teacher_notes:str):
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        temperature=0,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": f"""
                 #context#: i want to review a student's answer to a short response math problem containing images and provide feedback to the student.
                 #objective#: provide concise and constructive feedback to a fifth grade student so that the student can figure out what they did wrong with some scaffolding.
                 #tone#: positive, encouraging, and constructive.
                 #audience#: fifth grade student in the US.
                 #problem statement#: {problem_statement}
                 #solution#: {solution}
                 #answer#: {answer}
                 #teacher notes#: {teacher_notes}

                 #response#
                 keep the feedback concise, no more than 2 sentences, and never reveal answers directly.
                 """},
                {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                },
                },
            ],
            }
        ],
        max_tokens=1000, # careful with this 
        )

    return response.choices[0].message.content

@st.cache_data()
def summarize_analysis(analysis:str, solution:str, skills_tested:str):
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        temperature=0,
        messages=[
            {"role": "system", 
             "content": 'you provide feedback to a student on math problems. based on a detailed analysis for the student\'s response, provide short and specific feedback.'},
            {"role": "user",
            "content": f'''detailed analysis on the student's response to the question <analysis>{analysis}</analysis>. 
            provide short and specific feedback that follows these guidelines:
            - here are the skill(s) being assessed: <skill_tested>{skills_tested}</skills_tested>; feedback needs to reflect the skills being assessed.
            - focus on the areas where the student needs improvement.
            - keep it short, no more than 2 sentences; avoid qualifiers, encouragements, motivational text, etc. but remain age-appropriate for a fifth grader.
            - never reveal solution <solution>{solution}</solution>.
            - never point to a specific option of the question.
            - either point to the problem or ask guiding questions, avoid using general and vague words.
            ''',
            }],
        max_tokens=100, # careful with this
        )
    return response.choices[0].message.content

def grade_short_response_image(problem_statement:str,solution:dict, answer:str, image_url:str, teacher_notes:str, points:int=4) -> int:
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        temperature=0,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": f"""
                 You are a short response question grader for math grade 5.
                 given problem statement, optional solution, teacher's note, a fifth grade student's answer, and the total points, grade it.
                 problem statement: {problem_statement}
                 solution: {solution}
                 answer: {answer}
                 teacher notes: {teacher_notes}

                 Return an integer between 0 and {points}
                 """},
                {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                },
                },
            ],
            }
        ],
        )

    return int(response.choices[0].message.content)

def grade_short_answer(teacher_notes:str, solution:str, answer:str, points:int=4) -> int:
    response = client.chat.completions.create(
      model="gpt-4",
      temperature=0,
      messages=[
        {"role": "system"
         , "content": """
        You are a short answer question grader for math grade 5.
        given solution, teacher's note, and student's answer, and the total points, grade it."""},
        {"role": "user", "content": 
         f'''teacher note: {teacher_notes}
           solution: {solution} 
           student's answer: {answer}. 
         Return an integer between 0 and {points}'''},
      ]
    )
    return int(response.choices[0].message.content)

def calculate_multiple_select_score(solution:dict, answer:dict, points:int=4) -> int:
    """
    This function calculates the score for multiple select questions.
    It counts the number of correct options selected and incorrect options not selected,
    divides the total by the total number of options, multiplies by the total points of the question,
    and rounds down to the nearest integer.
    
    Args:
        solution (dict): The correct answers for the question.
        answer (dict): The student's answers for the question.
        total_points (int): The total points for the question.
    
    Returns:
        int: The calculated score for the question.
    """
    # Count correctly selected and correctly not selected options
    correct_selections = sum(answer[key] == solution[key] and solution[key] is True for key in solution)
    correct_deselections = sum(answer[key] == solution[key] and solution[key] is False for key in solution)

    # Calculate the total score
    total_options = len(solution)
    score = floor((correct_selections + correct_deselections) / total_options * points)
    
    return score

def strip_p_tags(text:str) -> str:
    """
    This function strips out <p> </p> tags from the given text.

    Args:
        text (str): The text containing <p> </p> tags.

    Returns:
        str: The text with <p> </p> tags removed.
    """
    return text.replace('<p>', '').replace('</p>', '')

def mathml_to_readable(expr):
    def parse_mathml(mathml_content):
        try:
            root = ET.fromstring(mathml_content)
        except ET.ParseError as e:
            return f"Error parsing MathML: {e}"

        def parse_element(element):
            if element.tag.endswith('mn'):
                return element.text
            elif element.tag.endswith('msup'):
                base = parse_element(element[0])
                exp = parse_element(element[1])
                return f"{base}^{exp}"
            elif element.tag.endswith('mo'):
                operator = html.unescape(element.text)
                if operator == '·':
                    return ' * '
                elif operator == ':':
                    return ' to '
                else:
                    return operator
            else:
                return ''.join(parse_element(child) for child in element)

        return parse_element(root)

    def extract_and_replace_mathml(text):
        mathml_pattern = r'(<math.*?</math>)'
        while True:
            match = re.search(mathml_pattern, text)
            if not match:
                break
            mathml_expr = match.group(1)
            readable_expr = parse_mathml(mathml_expr)
            text = text.replace(mathml_expr, readable_expr, 1)
        return text

    return extract_and_replace_mathml(expr)

if __name__ == "__main__":
    # set the page wide
    st.set_page_config(layout="wide")
    st.title("Math Multiple Select Assessment Question Response Analyzer")
    st.write("""---""")
    question_1 = {
        'statement': "Select **all** expressions that represent the volume of this rectangular prism in cubic units.",
        'image_url_old': 'https://kiddom-media-production.s3.amazonaws.com/IM/Math/6/rnmcnx6o0bnzg8ymqwv5dsu7l365',
        'image_url': 'https://i.ibb.co/qWzjX0n/q1.png',
        'solutions': {
            "A 3 * 4 * 5":True,
            "B 3 + 4 + 5":False,
            "C 20 + 20 + 20":True,
            "D 15 * 15 * 15 * 15":False,
            "E 5 * 12":True
        },
        'options': {
            "A 3 * 4 * 5":False,
            "B 3 + 4 + 5":False,
            "C 20 + 20 + 20":True,
            "D 15 * 15 * 15 * 15":False,
            "E 5 * 12":True
        },
        'teacher_notes': '''
        Students identify different ways to find the volume of a rectangular prism, including:
        multiplying length, width, and height
        decomposing into layers that are one cube thick and multiplying the number of cubes in one layer by the number of layers
        choosing a face as the base and multiplying its area and the corresponding height
        Students who select B or D are using the wrong operation. Students may not select C or E if they do not think about the different ways of decomposing the prism.
        '''
    }
    # standard_name | standard_category | standard_subcategory | standard_description
    # select  *
    # from kiddom_teacherdashboard.production.standard
    # where standard_name = '5.OA.A.2'
    question_1_skils = {
        '5.OA.A.2': "Operations and Algebraic Thinking. Write And Interpret Numerical Expressions. Write simple expressions that record calculations with whole numbers, fractions, and decimals, and interpret numerical expressions without evaluating them. For example, express the calculation â€œadd 8 and 7, then multiply by 2â€ as 2 Ã— (8 + 7). Recognize that 3 x (18,932 + 9.21) is three times as large as 18,932 + 9.21, without having to calculate the indicated sum or product.",
        '5.MD.C.5.a': 'Measurement and Data. Find the volume of a right rectangular prism with whole-number side lengths by packing it with unit cubes, and show that the volume is the same as would be found by multiplying the edge lengths, equivalently by multiplying the height by the area of the base. Represent threefold whole-number products as volumes, e.g., to represent the associative property of multiplication.'
    }
    question_1_skills_concatenated = '\n'.join(question_1_skils.values())
    # st.write(question_1_skills_concatenated)
    
    st.write(f"1. {question_1['statement']}")
    st.image(question_1['image_url'], caption="", use_column_width=False)

    question_1_options_checked = {}
    for option, correct in question_1['options'].items():
        question_1_options_checked[option] = st.checkbox(option, value=correct, key=option)

    full_score_fd = "Great job! You got it right!"
    with st.expander('answers | score | analysis | feedback'):
        st.write('question 1')
        col1, col2, col3, col4 = st.columns((1,1,2,1))
        with col1:
            st.write('*answer*', question_1_options_checked)
        with col2:
            score = calculate_multiple_select_score(solution=question_1['solutions'], answer=question_1_options_checked, points=4)
            st.write('*score*', score)
        with col3:
            if score == 4:
                st.write('*analysis*\n', full_score_fd)
                # st.audio(render_audio(full_score_fd))
            else:
                fd = analyze_multiple_select_image(problem_statement=question_1['statement'], solution=question_1['solutions'],
                                                                answer=question_1_options_checked, image_url=question_1['image_url'],
                                                                teacher_notes=question_1['teacher_notes'], skills_tested=question_1_skills_concatenated)
                st.write('*analysis*')
                st.write(fd)
        with col4:
            if score != 4:
                st.write("feedback\n")
                fd_a = summarize_analysis(fd, question_1['solutions'], question_1_skills_concatenated)
                st.write(fd_a)


   # add another multiple select question
    st.write("""---""")
    question_2 = {
        'url': 'https://app.kiddom.co/curriculum/668915/node/0ea5255a-6e31-42f7-951b-bac095a4679e:64f36058-5e4a-11ee-ac67-066a39b724af:ab40832d-574f-11ee-8f21-06dd2b7bf731',
        'other notes': 'problem 3',
        'statement': '<p>A cube has a side length of 8 inches.</p><p>Select <strong>all</strong>&nbsp;the values that&nbsp;represent the cube&rsquo;s volume in cubic inches.</p>', 
        'image_url_in_statement': None,
        'image_in_statement_alt': None, 
        'solutions': {
            'A <p><math xmlns="http://www.w3.org/1998/Math/MathML"><msup><mn>8</mn><mn>2</mn></msup></math></p>': False,
            'B <p><math xmlns="http://www.w3.org/1998/Math/MathML"><msup><mn>8</mn><mn>3</mn></msup></math></p>': True,
            'C <p><math xmlns="http://www.w3.org/1998/Math/MathML"><mn>6</mn><mo>&#183;</mo><msup><mn>8</mn><mn>2</mn></msup></math></p>': False,
            'D <p><math xmlns="http://www.w3.org/1998/Math/MathML"><mn>6</mn><mo>&#183;</mo><mn>8</mn></math></p>': False,
            'E <p><math xmlns="http://www.w3.org/1998/Math/MathML"><mn>8</mn><mo>&#183;</mo><mn>8</mn><mo>&#183;</mo><mn>8</mn></math></p>': True
            },
        'response': {
            'A <p><math xmlns="http://www.w3.org/1998/Math/MathML"><msup><mn>8</mn><mn>2</mn></msup></math></p>': True,
            'B <p><math xmlns="http://www.w3.org/1998/Math/MathML"><msup><mn>8</mn><mn>3</mn></msup></math></p>': True,
            'C <p><math xmlns="http://www.w3.org/1998/Math/MathML"><mn>6</mn><mo>&#183;</mo><msup><mn>8</mn><mn>2</mn></msup></math></p>': False,
            'D <p><math xmlns="http://www.w3.org/1998/Math/MathML"><mn>6</mn><mo>&#183;</mo><mn>8</mn></math></p>': False,
            'E <p><math xmlns="http://www.w3.org/1998/Math/MathML"><mn>8</mn><mo>&#183;</mo><mn>8</mn><mo>&#183;</mo><mn>8</mn></math></p>': True
            },
        'teacher_notes': None,
        'skills_tested': {
            '6.EE.A.1': "Category: Expressions and Equations.Sub_Category: Apply And Extend Previous Understandings Of Arithmetic To Algebraic Expressions. Description: Write and evaluate numerical expressions involving whole-number exponents."
        }
        
    }
    question_2['skills_tested_str'] = '\n'.join(question_2['skills_tested'].values())
    
    st.markdown(f"**OUR-G6-U1-EUA Problem 3**. ([link to original question]({question_2['url']})) {question_2['statement']}", unsafe_allow_html=True)
    

    question_2_options_checked = {}
    for option, correct in question_2['response'].items():
        question_2_options_checked[option] = st.checkbox(strip_p_tags(mathml_to_readable(option)), value=correct, key=option)


    # convert the mathml to readable text in question_2['solutions']
    question_2_solutions = {strip_p_tags(mathml_to_readable(k)):v for k,v in question_2['solutions'].items()}
    question_2_response = {strip_p_tags(mathml_to_readable(k)):v for k,v in question_2_options_checked.items()}
    with st.expander('answers | score | analysis | feedback'):
        st.write('Problem 3')
        col1, col2, col3, col4 = st.columns((1,1,2,1))
        with col1:
            st.write('*answer*',  question_2_response)
        with col2:
            score = calculate_multiple_select_score(
                solution=question_2_solutions, answer=question_2_response, points=4)
            st.write('*score*', score)
        with col3:
            if score != 4:
                analysis = analyze_multiple_select(
                    problem_statement=question_2['statement'], solution=question_2_solutions,
                    answer=question_2_response, 
                    teacher_notes=question_2["teacher_notes"], skills_tested=question_2['skills_tested_str'])
                st.write('*analysis*')
                st.write(analysis)
        with col4:
            if score != 4:
                st.write("feedback\n")
                feedback = summarize_analysis(analysis, question_2_solutions, question_2['skills_tested_str'])
                st.write(feedback)


    # add another multiple select question
    st.write("""---""")
    question_3 = {
        'url': 'https://app.kiddom.co/curriculum/668915/node/0ea5255a-6e31-42f7-951b-bac095a4679e:64f36058-5e4a-11ee-ac67-066a39b724af:ab40ef47-574f-11ee-9e8a-06dd2b7bf731',
        'other notes': 'problem 1',
        'statement': '<p>Select <strong>all</strong> the true statements.</p>', 
        'image_url_in_statement': 'https://kiddom-media-production.s3.us-east-2.amazonaws.com/OUR/math/68/v2/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBa1kxIiwiZXhwIjpudWxsLCJwdXIiOiJibG9iX2lkIn19--9738a045918a2d388d4614995fc937d1ff52a122/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBZzZGRzF6WDIxaGRHaGZaR2xuYVhSaGJBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--89678ca32ceb3b39b6bd3f12552ca73d54236306/6.2.EA.smilytrianglesquare.png',
        'image_in_statement_alt': "", 
        'solutions': {
            'A <p>The ratio of triangles to squares is 2 to 4.</p>': True,
            'B <p>The ratio of squares to smiley faces is&nbsp;<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>6</mn><mo>:</mo><mn>4</mn></math>.&nbsp;</p>': False,
            'C <p>The ratio of smiley faces to triangles is 6 to 4.&nbsp;</p>': False,
            'D <p>There are two squares for every triangle.</p>': True,
            'E <p>There are two triangles for every smiley face.</p>': False,
            'F <p>There are three smiley faces for every triangle.</p>': True
            },
        'response': {
            'A <p>The ratio of triangles to squares is 2 to 4.</p>': True,
            'B <p>The ratio of squares to smiley faces is&nbsp;<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>6</mn><mo>:</mo><mn>4</mn></math>.&nbsp;</p>': False,
            'C <p>The ratio of smiley faces to triangles is 6 to 4.&nbsp;</p>': False,
            'D <p>There are two squares for every triangle.</p>': False,
            'E <p>There are two triangles for every smiley face.</p>': False,
            'F <p>There are three smiley faces for every triangle.</p>': False
            },
        'teacher_notes': None,
        'skills_tested': {
            '6.RP.A.1': """Category: Ratios and Proportional Relationships
            Sub_Category: Understand Ratio Concepts And Use Ratio Reasoning To Solve Problems.
            Description: Understand the concept of a ratio and use ratio language to describe a ratio relationship between two quantities. For example, â€œThe ratio of wings to beaks in the bird house at the zoo was 2:1, because for every 2 wings there was 1 beak.â€ â€œFor every vote candidate A received, candidate C received nearly three votes.
            """
        }
        
    }
    question_3['skills_tested_str'] = '\n'.join(question_3['skills_tested'].values())

    st.markdown(f"**OUR-G6-U2-EUA Problem 1**. ([link to original question]({question_3['url']})) {question_3['statement']}", unsafe_allow_html=True)
    # display the image
    st.image(question_3['image_url_in_statement'], caption="", use_column_width=False)
    # display the options
    question_3_options_checked = {}
    for option, correct in question_3['response'].items():
        question_3_options_checked[option] = st.checkbox(strip_p_tags(mathml_to_readable(option)), value=correct, key=option)

    # convert the mathml to readable text in question_2['solutions']
    question_3_solutions = {strip_p_tags(mathml_to_readable(k)):v for k,v in question_3['solutions'].items()}
    question_3_response = {strip_p_tags(mathml_to_readable(k)):v for k,v in question_3_options_checked.items()}
    with st.expander('answers | score | analysis | feedback'):
        st.write('Problem 3')
        col1, col2, col3, col4 = st.columns((1,1,2,1))
        with col1:
            st.write('*answer*',  question_3_response)
        with col2:
            score = calculate_multiple_select_score(
                solution=question_3_solutions, answer=question_3_response, points=4)
            st.write('*score*', score)
        with col3:
            if score != 4:
                analysis = analyze_multiple_select(
                    problem_statement=question_3['statement'], solution=question_3_solutions,
                    answer=question_3_response, 
                    teacher_notes=question_3["teacher_notes"], skills_tested=question_3['skills_tested_str'])
                st.write('*analysis*')
                st.write(analysis)
        with col4:
            if score != 4:
                st.write("feedback\n")
                feedback = summarize_analysis(analysis, question_3_solutions, question_3['skills_tested_str'])
                st.write(feedback)