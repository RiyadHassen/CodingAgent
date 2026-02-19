#pip install strands-agents strands-agents-tools
from strands import Agent
agent = Agent(tools = [ calculator, current_time])

#
message = """ Calculate the sum of 5 and 10, and also tell me the current time. """
response = agent(message)
print(response)


from strands_tools import file_read, file_write

#define a model

# 
system_prompt = """

"""


#define the agent
#wirting custom tools
from strands import tool



agent = Agent(
    model = model_id,
    system_prompt = system_prompt,
    tools = [
        file_read,
        file_write
    ]
)

#create a custom tool as a python function using the @tool decorator
@tool
def letter_counter(word, letter):
    "count occurrences of a specfic letter in a word "
    if not isinstance(word,str) or not isinstance(letter, str):
        return 0

    return word.lower().count(letter.lower())


