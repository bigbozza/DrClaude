Journal to AI Therapy 

 

The app at the outset is simple, it's a daily journal with a SQlite db to store the entries. But it has the ability to send the entries to a reasoning LLM as context. 

The user can fill out information like their overall goal from the therapy (if there is one), age, sex, marital status, children, siblings, historical abuses, substance abuses – or not, it’s entirely up to them as to what is stored. Or, in the course of speaking to the LLM, if key information is discovered (like historical abuse) the notes from the therapist can be updated so that is added to the context moving forward. 

The LLM can then provide continued and improving therapy sessions based on the journal entries, user provided history, generated therapist notes and the users goals (if any). 

Now, people aren't likely to like the idea of handing all of this information over for storage on a remote server, so we store all the data on the device, encrypted with a vault password. 

When the user opens the app they must enter the password to unlock the vault, then they can add a new journal entry or they can start a therapy session with reasoning LLM. 

The user can select between Freudian/Yungian/CBT etc as a framework for the therapist and this will guide the notes take and responses of the LLM. 

The SQlite db will store each day's journal(s) along with therapist notes and patient history. After 2 months  have passed, the daily data from the month before last will be condensed into a month long block. This is to keep the LLMs context fresh with something that happened near the end of the last month but still keeping context down for older interactions. This will help prevent ending up with a somewhat forgetful LLM around the 1st of every month. 

This project is to be made in python

It will take an openai, anthropic or ollama api key and will have a model selector. The default is anthropic claude-3-7-sonnet-20250219.

