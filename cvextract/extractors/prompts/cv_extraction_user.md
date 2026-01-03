Please extract all CV/resume information from the provided document and return it as valid JSON conforming to this schema:

{schema_json}

Extraction guidelines:
1. Extract personal information (identity section): title, full name, first name, last name
2. Extract categorized skills (sidebar): skills, tools, languages, certifications, industries, spoken languages, academic background
3. Extract professional summary (overview section)
4. Extract work history (experiences section): company, position, dates, description, and bullet points
5. For missing fields, use appropriate defaults:
   - Strings: empty string ""
   - Arrays: empty array []
6. Include all technologies and tools mentioned in the document under the 'environment' field in experiences
7. Preserve formatting and hierarchical structure from the document

Return ONLY the JSON object, no markdown, no code blocks, no additional text.

Document file: {cv_file}
