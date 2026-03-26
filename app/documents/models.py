class BusinessDocument(db.Model):
    __tablename__ = 'business_document'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Document metadata
    title = db.Column(db.String(200), nullable=False)
    doc_type = db.Column(db.String(50), nullable=False)  # 'business_plan', 'pitch_deck', 'sop', etc.
    content = db.Column(db.Text, nullable=False)  # Generated content (HTML/Markdown)
    version = db.Column(db.Integer, default=1)
    
    # Status & metadata
    status = db.Column(db.String(20), default='draft')  # draft, published, archived
    generated_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    # Relationships
    startup = db.relationship('Startup', backref='documents')
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'title': self.title,
            'doc_type': self.doc_type,
            'content': self.content[:200] + '...' if len(self.content) > 200 else self.content,  # Preview
            'version': self.version,
            'status': self.status,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None
        }