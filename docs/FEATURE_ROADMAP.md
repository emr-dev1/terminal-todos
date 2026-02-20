# Terminal Todos - Feature Roadmap

## Selected Features for Implementation

### 1. Recurring/Repeating Todos
Essential for ongoing tasks:
```
/todo Weekly standup --repeat every monday
/todo Pay rent --repeat monthly
```
- Auto-create new instance when completed
- Different patterns: daily, weekly, monthly, custom
- Show next occurrence date

### 2. Projects & Todo Grouping
Organize related todos:
```
/project client-alpha
/todo Review contract --project client-alpha
/focus project client-alpha  # Focus on all project todos
```
- Filter by project
- Project progress tracking
- Focus suggestions could be project-aware

### 3. Tags/Labels System
More flexible than note-based organization:
```
/todo Fix login bug #bug #backend #urgent
/list #bug  # Show all bug-related todos
```
- Multi-tag support
- Tag-based filtering
- AI could auto-suggest tags

### 4. Smart Scheduling Assistant
AI suggests when to do tasks:
```
User: "when should I do the design review?"
AI: "Based on your patterns, mornings work best for creative tasks.
     You have 3 high-priority items due today. I suggest:
     - 9am-10am: Design review (high energy needed)
     - 10am-11am: Client call (scheduled)
     - After lunch: Administrative tasks"
```

---

## Implementation Notes

### Priority Order
1. Tags/Labels System (foundation for other features)
2. Projects & Todo Grouping (organizational structure)
3. Recurring/Repeating Todos (high-value quality of life)
4. Smart Scheduling Assistant (leverages AI + patterns)

### Architecture Considerations
- Tags: Add `tags` field to Todo model (similar to Note tags)
- Projects: Add `project_id` foreign key to Todo model, new Project model
- Recurring: Add `recurrence_pattern` JSON field to Todo model
- Scheduling: New agent tool leveraging existing LLM + todo metadata

---

## Status Tracking

| Feature | Status | Started | Completed |
|---------|--------|---------|-----------|
| Tags/Labels System | Not Started | - | - |
| Projects & Grouping | Not Started | - | - |
| Recurring Todos | Not Started | - | - |
| Smart Scheduling | Not Started | - | - |
