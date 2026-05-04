-- ============================================================
-- seed_data.sql  –  Realistic sample data for the Observatory
-- ============================================================

-- ----------------------------------------------------------
-- Clusters (initial seed – will be updated by ClusteringAgent)
-- ----------------------------------------------------------
INSERT OR IGNORE INTO clusters (name, description, keywords) VALUES
('Machine Learning & AI Research',    'Opportunities in ML, deep learning, and AI research labs',     'machine learning, deep learning, neural network, AI, research'),
('Data Science & Analytics',          'Data science roles, analytics internships, and DS courses',     'data science, analytics, pandas, SQL, visualization'),
('Natural Language Processing',       'NLP research, text mining, and language model projects',        'NLP, text, language model, BERT, transformers'),
('Computer Vision & Robotics',        'Vision systems, autonomous vehicles, and robotics',             'computer vision, image, robotics, OpenCV, SLAM'),
('Scholarships & Funding Programs',   'Fellowships, grants, and academic funding opportunities',       'scholarship, fellowship, grant, funding, stipend');

-- ----------------------------------------------------------
-- Users (sample student profiles)
-- ----------------------------------------------------------
INSERT OR IGNORE INTO users (name, email, profile, interests, skills, level) VALUES
('Alice Martin',   'alice@university.edu',   'MSc Data Science student researching recommendation systems',
 'machine learning, recommendation systems, graph neural networks',
 'Python, TensorFlow, scikit-learn, SQL, pandas', 'master'),

('Bob Chen',       'bob@university.edu',     'Bachelor CS student interested in NLP and sentiment analysis',
 'NLP, sentiment analysis, text classification, chatbots',
 'Python, NLTK, spaCy, Flask, JavaScript', 'bachelor'),

('Claire Duval',   'claire@university.edu',  'PhD candidate in computer vision and autonomous systems',
 'computer vision, autonomous driving, SLAM, robotics',
 'Python, C++, OpenCV, PyTorch, ROS', 'phd'),

('David Okonkwo',  'david@university.edu',   'Postdoc researcher in federated learning and privacy',
 'federated learning, privacy, distributed systems, AI safety',
 'Python, TensorFlow, Kubernetes, cryptography', 'postdoc'),

('Emma Wilson',    'emma@university.edu',    'Master student in AI for healthcare and biomedical data',
 'healthcare AI, medical imaging, bioinformatics, genomics',
 'Python, R, scikit-learn, deep learning, statistics', 'master');

-- ----------------------------------------------------------
-- Opportunities – Internships
-- ----------------------------------------------------------
INSERT OR IGNORE INTO opportunities (type, title, description, source, location, eligibility, deadline, url, category) VALUES

('internship',
 'Machine Learning Engineering Intern – Google DeepMind',
 'Join DeepMind to work on cutting-edge machine learning research and engineering. You will design and implement scalable ML pipelines, collaborate with world-class researchers, and contribute to real-world AI applications. Strong background in Python, TensorFlow or JAX required. Experience with distributed training is a plus.',
 'DeepMind Careers', 'London, UK / Remote', 'Master or PhD students in CS, ML, or related field', '2025-06-30',
 'https://deepmind.google/careers/', 'internship'),

('internship',
 'Data Science Research Intern – Meta AI',
 'Work with Meta AI Research to develop novel data science methodologies. Projects span recommendation systems, social network analysis, and large-scale data pipelines. Candidates should have experience with PyTorch, SQL, and statistical modeling.',
 'Meta Careers', 'Menlo Park, CA / Remote', 'Bachelor or Master students in Data Science, Statistics, CS', '2025-05-15',
 'https://www.metacareers.com/', 'internship'),

('internship',
 'NLP Research Intern – Hugging Face',
 'Help build the next generation of open-source language models. You will fine-tune transformers, build evaluation benchmarks, and contribute to the Hugging Face Hub ecosystem. Must have hands-on experience with transformers library and Python.',
 'Hugging Face Jobs', 'Paris, France / Remote', 'Master or PhD students in NLP, ML, or Computational Linguistics', '2025-07-01',
 'https://huggingface.co/jobs', 'internship'),

('internship',
 'Computer Vision Intern – Tesla Autopilot',
 'Develop and optimize computer vision algorithms for autonomous driving at scale. Work with massive real-world datasets, implement 3D perception models, and deploy to Tesla fleet. Strong C++ and Python skills required.',
 'Tesla Careers', 'Palo Alto, CA', 'Bachelor, Master, or PhD in CS, ECE, or Robotics', '2025-06-01',
 'https://www.tesla.com/careers', 'internship'),

('internship',
 'AI for Healthcare Intern – Philips Research',
 'Apply machine learning and computer vision to medical imaging problems. Contribute to FDA-grade software development, work alongside clinical experts, and publish research. Background in medical image analysis preferred.',
 'Philips Research', 'Amsterdam, Netherlands / Remote', 'Master or PhD students in Biomedical Engineering, CS, or related', '2025-08-01',
 'https://www.philips.com/careers', 'internship'),

-- ----------------------------------------------------------
-- Opportunities – Scholarships & Fellowships
-- ----------------------------------------------------------
('scholarship',
 'Google PhD Fellowship in Machine Learning',
 'The Google PhD Fellowship Program recognizes and supports exceptional PhD students in CS and related fields. Fellows receive a generous stipend, access to Google researchers as mentors, and opportunities to visit Google research labs. Focus areas include machine learning, systems, and human-computer interaction.',
 'Google Research', 'Global', 'PhD students in their 2nd or 3rd year in CS or related field', '2025-04-15',
 'https://research.google/outreach/phd-fellowship/', 'scholarship'),

('fellowship',
 'CIFAR AI Chairs Fellowship – Canada',
 'CIFAR AI Chairs support world-leading AI researchers in Canada. This prestigious fellowship provides research funding, collaboration opportunities with CIFAR networks, and access to a global community of AI researchers.',
 'CIFAR', 'Canada', 'Outstanding researchers in AI/ML with PhD degree', '2025-09-01',
 'https://cifar.ca/ai/', 'fellowship'),

('scholarship',
 'Marie Skłodowska-Curie Doctoral Fellowship – EU',
 'Fully-funded doctoral fellowship under the European Union Horizon programme. Candidates pursue interdisciplinary research in AI, data science, and related fields across European universities. Monthly living and mobility allowances provided.',
 'European Commission', 'European Union', 'Researchers within 4 years of PhD, any nationality', '2025-10-31',
 'https://marie-sklodowska-curie-actions.ec.europa.eu/', 'scholarship'),

('scholarship',
 'NVIDIA Graduate Fellowship – GPU Computing Research',
 'Support for graduate students using NVIDIA technology in research. Areas include deep learning, computer graphics, autonomous vehicles, and scientific computing. Fellows receive a monetary award, GPU hardware, and mentorship.',
 'NVIDIA Research', 'Global', 'Full-time PhD students in their 2nd year or beyond', '2025-06-01',
 'https://research.nvidia.com/graduate-fellowships', 'scholarship'),

-- ----------------------------------------------------------
-- Opportunities – Courses & Certifications
-- ----------------------------------------------------------
('course',
 'Deep Learning Specialization – Coursera (Andrew Ng)',
 'Master deep learning fundamentals through 5 courses: Neural Networks, Improving Deep Neural Networks, Structuring ML Projects, CNNs, and Sequence Models. Hands-on assignments in Python and TensorFlow. Industry-recognized certificate upon completion.',
 'Coursera / DeepLearning.AI', 'Online', 'Anyone with basic Python and linear algebra knowledge', '2025-12-31',
 'https://www.coursera.org/specializations/deep-learning', 'course'),

('course',
 'MLOps Specialization – Coursera',
 'Learn to deploy and maintain machine learning systems in production. Covers data pipelines, model monitoring, drift detection, CI/CD for ML, and Kubernetes. Practical projects using real industry tools.',
 'Coursera / DeepLearning.AI', 'Online', 'ML practitioners with basic Python knowledge', '2025-12-31',
 'https://www.coursera.org/specializations/mlops-machine-learning-duke', 'course'),

('course',
 'Applied Data Science with Python – edX (MIT)',
 'Comprehensive data science curriculum from MIT covering statistics, machine learning, data visualization, and applied projects. Includes capstone project with real datasets.',
 'edX / MIT', 'Online', 'Anyone with introductory programming background', '2025-12-31',
 'https://www.edx.org/professional-certificate/mit-data-science', 'course'),

('course',
 'Reinforcement Learning Specialization – Coursera (Alberta)',
 'Four-course specialization covering fundamentals and practice of RL: Bandits, Model-Free Methods, Prediction and Control with Function Approximation, and a Capstone project.',
 'Coursera / University of Alberta', 'Online', 'Students with ML fundamentals knowledge', '2025-12-31',
 'https://www.coursera.org/specializations/reinforcement-learning', 'course'),

-- ----------------------------------------------------------
-- Opportunities – Research Projects
-- ----------------------------------------------------------
('research_project',
 'Open Source Contribution – Scikit-Learn Core Development',
 'Contribute to scikit-learn, the industry-standard ML library. Work on algorithm implementations, documentation, and testing. Mentored by core maintainers. Great for building open-source portfolio and ML engineering skills.',
 'scikit-learn Community', 'Remote / Global', 'Any level with Python proficiency', '2025-12-31',
 'https://scikit-learn.org/stable/developers/contributing.html', 'research_project'),

('research_project',
 'AI for Climate Change Research Project – ClimateAI',
 'Research project applying machine learning to climate modeling, extreme weather prediction, and carbon footprint analysis. Collaborate with climate scientists and ML researchers.',
 'ClimateAI Research', 'Remote / San Francisco, CA', 'Master or PhD students in ML, atmospheric science, or related', '2025-07-15',
 'https://climate.ai/research/', 'research_project'),

('research_project',
 'Federated Learning for Healthcare – IEEE Research Initiative',
 'Research into privacy-preserving machine learning for hospitals and health systems. Design federated protocols, analyze differential privacy guarantees, and prototype on real health data.',
 'IEEE Technical Committee on AI', 'Remote / Global', 'PhD students or postdocs in ML, distributed systems, privacy', '2025-08-31',
 'https://www.ieee.org/research/', 'research_project'),

-- ----------------------------------------------------------
-- Opportunities – Postdoc Positions
-- ----------------------------------------------------------
('postdoc',
 'Postdoctoral Researcher in Large Language Models – ETH Zurich',
 'ETH Zurich AI Center seeks a postdoctoral researcher to work on efficient training of large language models, alignment techniques, and evaluation frameworks. Strong publication record required. 2-year position with competitive salary.',
 'ETH Zurich AI Center', 'Zurich, Switzerland', 'PhD in CS, ML, NLP or related field completed within 5 years', '2025-06-30',
 'https://ai.ethz.ch/open-positions/', 'postdoc'),

('postdoc',
 'Postdoc in Reinforcement Learning – Carnegie Mellon University',
 'Join the CMU Robotics Institute to research deep reinforcement learning for robotic manipulation and locomotion. Work with state-of-the-art robot platforms and collaborate with industry partners.',
 'CMU Robotics Institute', 'Pittsburgh, PA, USA', 'PhD in Robotics, CS, ECE, or related field', '2025-09-01',
 'https://www.ri.cmu.edu/ri-jobs/', 'postdoc'),

('postdoc',
 'Visiting Researcher in AI Safety – Oxford Future of Humanity Institute',
 'Research AI alignment, interpretability, and long-term AI safety. Collaborate with leading philosophers, mathematicians, and AI researchers at the Oxford FHI. Flexible duration 6-24 months.',
 'Oxford FHI', 'Oxford, UK', 'PhD in CS, Mathematics, Philosophy of Mind, or related', '2025-11-01',
 'https://www.fhi.ox.ac.uk/vacancies/', 'postdoc');
