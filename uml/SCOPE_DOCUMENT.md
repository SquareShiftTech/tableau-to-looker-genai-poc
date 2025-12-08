# Scope Document - Assessment Accelerator Platform

## Document Information
- **Project Name:** Assessment Accelerator Platform
- **Document Version:** 1.0
- **Date:** 2024
- **Prepared By:** SquareShift Team

---

## 1. Executive Summary

The Assessment Accelerator Platform is a system designed to process Business Intelligence (BI) files from various BI platforms and generate comprehensive migration assessment reports. The platform facilitates the analysis and assessment of BI assets from Tableau, Power BI, MicroStrategy, and Cognos platforms, enabling clients to understand their current BI landscape and plan for migration.

---

## 2. System Description

The Assessment Accelerator Platform is a centralized system that:
- Processes BI files collected from multiple BI platforms
- Analyzes BI assets and metadata
- Generates migration assessment reports in PDF format
- Provides utilities for clients to collect BI files from their source platforms

---

## 3. In-Scope Components

### 3.1 Core Platform Functionality
- **BI File Processing Engine**
  - Processing of BI files collected from Tableau, Power BI, MicroStrategy, and Cognos
  - File validation and parsing capabilities
  - Metadata extraction and analysis

- **Assessment Report Generation**
  - Automated generation of migration assessment reports
  - PDF report creation and formatting
  - Report delivery mechanisms

- **Client Utility Distribution**
  - Provision of client-side utilities for BI file collection
  - Utility download functionality
  - Support for multiple BI platform collectors

### 3.2 Integration Points
- **Google Cloud Storage (GCS) Integration**
  - Read access to client's GCS bucket
  - File retrieval from specified GCS paths
  - Support for standard GCS authentication mechanisms

- **Email Delivery System**
  - PDF report delivery via email
  - Email notification capabilities

### 3.3 User Interfaces
- **Internal Team Interface**
  - Assessment triggering functionality
  - GCS path configuration
  - Report generation controls
  - Report viewing and management

- **Client Utility Interface**
  - Utility download portal
  - Utility execution interface (client-side)

### 3.4 Supported BI Platforms
- **Tableau Server**
  - File collection utility support
  - Metadata extraction capabilities

- **Power BI**
  - File collection utility support
  - Metadata extraction capabilities

- **MicroStrategy**
  - File collection utility support
  - Metadata extraction capabilities

- **Cognos**
  - File collection utility support
  - Metadata extraction capabilities

---

## 4. Out-of-Scope Components

### 4.1 Client-Side Operations
- **BI Platform Access Management**
  - The platform does not manage client's BI platform credentials
  - The platform does not directly access client's BI platforms
  - Client is responsible for providing necessary access to their BI platforms

- **File Collection Execution**
  - The platform does not execute file collection utilities on client infrastructure
  - Client Data Engineer is responsible for running utilities and collecting files
  - The platform does not manage or monitor utility execution on client side

### 4.2 BI Platform Modifications
- **Source Platform Changes**
  - The platform does not modify or interact with source BI platforms
  - No write operations to Tableau, Power BI, MicroStrategy, or Cognos
  - No migration execution capabilities

### 4.3 Advanced Features
- **Real-time Monitoring**
  - Real-time assessment progress monitoring is out of scope
  - Live dashboard for assessment status is not included

- **Automated Migration**
  - The platform does not perform actual migration of BI assets
  - Migration execution tools are not part of this scope

- **Version Control Integration**
  - Git or other version control system integration is out of scope

- **Collaboration Features**
  - Multi-user collaboration features
  - Commenting or annotation capabilities on reports

### 4.4 Infrastructure Components
- **Client GCS Bucket Management**
  - The platform does not create or manage client's GCS buckets
  - Client is responsible for GCS bucket setup and configuration
  - The platform only reads from provided GCS paths

---

## 5. Key Actors and Roles

### 5.1 Client Data Engineer
**Responsibilities:**
- Downloads client utility from the Assessment Accelerator Platform
- Executes utility to collect BI files from client's BI platforms (Tableau, Power BI, MicroStrategy, Cognos)
- Uploads collected BI files to client's GCS bucket
- Receives PDF assessment reports via email

**Interactions:**
- Downloads utility from platform
- Runs collection utilities on client infrastructure
- Manages file uploads to GCS
- Receives reports via email

### 5.2 Internal Team (SquareShift)
**Responsibilities:**
- Triggers assessment processes
- Provides GCS path configuration
- Manages report generation
- Sends PDF reports to Client Data Engineer via email

**Interactions:**
- Configures assessment parameters
- Initiates assessment workflows
- Reviews and manages generated reports
- Coordinates report delivery to clients

---

## 6. External Systems and Dependencies

### 6.1 Client's BI Platforms
**Tableau Server**
- Source of BI files and metadata
- Client Data Engineer runs utility to collect files
- No direct integration with Assessment Accelerator Platform

**Power BI**
- Source of BI files and metadata
- Client Data Engineer runs utility to collect files
- No direct integration with Assessment Accelerator Platform

**MicroStrategy**
- Source of BI files and metadata
- Client Data Engineer runs utility to collect files
- No direct integration with Assessment Accelerator Platform

**Cognos**
- Source of BI files and metadata
- Client Data Engineer runs utility to collect files
- No direct integration with Assessment Accelerator Platform

### 6.2 Client's GCS Bucket
**Purpose:**
- Storage location for collected BI files
- Intermediate storage between file collection and platform processing

**Integration:**
- Assessment Accelerator Platform reads files from specified GCS paths
- Client Data Engineer uploads collected files to GCS
- Platform requires read access to client's GCS bucket

**Dependencies:**
- GCS bucket must be accessible to the platform
- Appropriate authentication and authorization must be configured
- Client is responsible for GCS bucket setup and maintenance

---

## 7. Key Processes and Workflows

### 7.1 Assessment Workflow
1. **Utility Distribution**
   - Client Data Engineer downloads utility from Assessment Accelerator Platform

2. **File Collection**
   - Client Data Engineer runs utility against each BI platform (Tableau, Power BI, MicroStrategy, Cognos)
   - Utility collects BI files and metadata from source platforms
   - Collected files are stored locally by Client Data Engineer

3. **File Upload**
   - Client Data Engineer uploads collected files to Client's GCS Bucket

4. **Assessment Trigger**
   - Internal Team (SquareShift) triggers assessment process
   - Internal Team provides GCS path to uploaded files

5. **File Processing**
   - Assessment Accelerator Platform reads files from Client's GCS Bucket
   - Platform processes BI files and extracts metadata
   - Platform performs analysis and assessment

6. **Report Generation**
   - Platform generates PDF assessment report
   - Report is made available to Internal Team

7. **Report Delivery**
   - Internal Team sends PDF report to Client Data Engineer via email
   - Platform may also send reports directly to Client Data Engineer

### 7.2 Data Flow
```
Client BI Platforms → Client Utility → Client Data Engineer → GCS Bucket → Assessment Platform → PDF Report → Email Delivery
```

---

## 8. Deliverables

### 8.1 Platform Components
- Assessment Accelerator Platform (core system)
- Client utilities for BI file collection (Tableau, Power BI, MicroStrategy, Cognos)
- Utility download portal
- Internal team interface for assessment management

### 8.2 Documentation
- User guide for Client Data Engineers
- User guide for Internal Team
- Utility installation and execution guide
- API documentation (if applicable)
- GCS integration guide

### 8.3 Reports
- Migration assessment PDF reports
- Report templates and formats
- Sample reports for reference

---

## 9. Assumptions

1. **Client Infrastructure**
   - Client has access to their BI platforms (Tableau, Power BI, MicroStrategy, Cognos)
   - Client has a GCS bucket set up and configured
   - Client Data Engineer has necessary permissions to access BI platforms and GCS

2. **Network and Access**
   - Client's GCS bucket is accessible from Assessment Accelerator Platform
   - Appropriate network connectivity and firewall rules are in place
   - Authentication credentials are properly configured

3. **File Formats**
   - BI platforms export files in formats that can be processed by the platform
   - File formats are consistent and well-documented

4. **User Capabilities**
   - Client Data Engineer has technical knowledge to run utilities
   - Internal Team has access to trigger assessments and manage reports

---

## 10. Constraints

1. **Platform Access**
   - Assessment Accelerator Platform does not have direct access to client's BI platforms
   - All file collection must be performed client-side using provided utilities

2. **Storage**
   - Platform does not provide storage for client files
   - Client must maintain their own GCS bucket for file storage

3. **Processing**
   - Assessment processing is triggered manually by Internal Team
   - Real-time or automated assessment triggering is not supported

4. **Report Delivery**
   - Report delivery is primarily via email
   - Alternative delivery mechanisms may be limited

5. **BI Platform Versions**
   - Utility compatibility may be limited to specific versions of BI platforms
   - Older or unsupported versions may not be fully supported

---

## 11. Success Criteria

1. **Functionality**
   - Platform successfully processes BI files from all supported platforms
   - Assessment reports are generated accurately and completely
   - Utilities successfully collect files from client BI platforms

2. **Performance**
   - Platform processes files within acceptable timeframes
   - Reports are generated and delivered in a timely manner

3. **Usability**
   - Client Data Engineers can successfully download and execute utilities
   - Internal Team can efficiently trigger assessments and manage reports

4. **Integration**
   - GCS integration works reliably
   - Email delivery is successful and consistent

---

## 12. Risks and Mitigations

### 12.1 Technical Risks
- **Risk:** GCS access issues preventing file retrieval
  - **Mitigation:** Clear documentation on GCS setup and authentication requirements

- **Risk:** Utility compatibility issues with different BI platform versions
  - **Mitigation:** Version testing and clear compatibility matrix

- **Risk:** Large file processing performance issues
  - **Mitigation:** Performance optimization and file size limits

### 12.2 Process Risks
- **Risk:** Client Data Engineer errors in file collection
  - **Mitigation:** Comprehensive utility documentation and support

- **Risk:** Delays in file upload to GCS
  - **Mitigation:** Clear timelines and communication protocols

---

## 13. Future Considerations (Out of Scope for Current Phase)

The following items are identified for potential future phases but are explicitly out of scope for the current implementation:

- Direct BI platform integration (bypassing client utilities)
- Real-time assessment dashboards
- Automated assessment scheduling
- Multi-tenant support with client isolation
- Advanced analytics and visualization in reports
- Migration execution capabilities
- Version control and change tracking
- Collaborative features for report review

---

## 14. Approval

**Prepared By:**
_________________________
[Name, Title, Date]

**Reviewed By:**
_________________________
[Name, Title, Date]

**Approved By:**
_________________________
[Name, Title, Date]

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024 | SquareShift Team | Initial scope document based on context diagram |
