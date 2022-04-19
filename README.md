# Gator Computational Cloud

![BuiltWith](https://img.shields.io/badge/Built%20With-Python-blue?style=flat&logo=python&logoColor=yellow)
[![codecov](https://codecov.io/gh/Nathandloria/gator-computational-cloud/branch/main/graph/badge.svg?token=YZBA3ZW2II)](https://codecov.io/gh/Nathandloria/gator-computational-cloud)
[![buildstatus](https://github.com/Nathandloria/gator-computational-cloud/workflows/lintandtest/badge.svg)](https://github.com/Nathandloria/gator-computational-cloud/actions)

![logo](img/gcc_logo.jpeg)

A lightweight framework for the execution of scientific workflows.

## Overview

A scientific workflow is a cluster of nodes that work together to accomplish an end goal. When executing a workflow, especially one associated with big data, there is often a massive amount of data and time overhead to work around. Because of this, there is a need for efficient and easy-to-use software that allows for the execution of workflows on obscure computing resources. This new model mitigates the need for massive infrastructure investments by the party that is executing a workflow. Additionally, the demand for efficient task scheduling solutions is ever-increasing. All of these are issues that can be tackled with the proper implementation of a grid computing system. This grid computing approach combined with efficient task scheduling is the focus of my project: Gator Computational Cloud (GCC). GCC is a lightweight web framework that utilizes a generic task scheduling algorithm to schedule jobs in a cloud environment. This framework intelligently manages dependencies and takes a multi-threaded execution approach to increase efficiency. To execute nodes, GCC takes advantage of the Amazon AWS API to provision virtual machines. Once provisioned, the tool completes the execution and transfers any dependencies to their corresponding VM in real-time utilizing an intelligent socket infrastructure. The goal of the project is to provide a lightweight and user-friendly environment for workflow execution, while also ensuring a powerful and efficient backend that completes a user’s workflow with ease. To achieve this, some preliminary experimentation has taken place to ensure the effectiveness of the tool.

## Initial Steps

Gator Computational Cloud does not currently have a package that is installable through the pip or pipx repositories. This is to ensure that a true XaaS approach is adopted for the software. Instead, the functionalities of the tool can be accessed by navigating to <https://gatorcompcloud.com/>.

### Logging In

If you already have an account with gator computational cloud, the landing page will accept your username and password and redirect you to your account dashboard.

### Signing Up

Once on the landing page, you will need to create an account if you do not already have one. Navigate to the button that says `Sign up`. When this button is clicked it will redirect you to a signup page where you can create an account with your own credentials. Upon completion of this form, you will be logged in and redirected to your account dashboard.

### Account Dashboard

Upon successful authentication, you will be redirected to your account dashboard. This screen displays a welcome message and contains the links to three separate pages: the external account credential page, the workflow page, and the machine pool page. If your external account credentials are not yet set up, any attempt to reach a different page will redirect you to the external account credential page.

### External Account Credentials

On this page, you will be presented with two sections: one section for configuring Dropbox credentials, and another for configuring AWS credentials. If both of these items are complete, a thumbs up will be displayed along with a short success message to let you know. If they are not set up, you will be presented with options to configure both.

For Dropbox credentials, clicking on the configure button will take you to Dropbox’s login page where you will be asked to log in and give `GatorCompCloud` authorization to your account. The application cannot see files outside of its application folder. Once this is complete, a valid refresh token will be generated for your account and can be viewed from the web interface.

For AWS credentials, a simple form will be presented to you. Once you get your credentials from the AWS IAM console associated with your account, you can paste them into the form and submit it. The required credentials are a valid access and secret key.

### Machine Pool

The machine pool is an important aspect of Gator Computational Cloud. To utilize it, you can input a machine’s IP and PEM file into the form, as well as a unique identifier, and submit the form. This machine will not be utilized during any workflow execution that is associated with your account. It is important to note that, without ports 22 and 80 being enabled on the machine, it will not work for the workflow. If no other virtual machine is available for a node, either from the specification file or machine pool, it will be created using AWS and terminated upon successful workflow completion.

## Managing Workflows

Workflows are an integral part of Gator Computational Cloud. This is where you can define the computational payloads to be executed in the cloud. The steps for developing a successful workflow will be discussed in a later section.

### Submitting Workflows

To submit a workflow, you must add the “GatorCompCloud” application to your Dropbox account. You can do this through the web interface using the steps outlined above. Once the `Apps` folder exists in your Dropbox console, navigate to `Apps/GatorCompCloud` and place your valid workflow folder into this directory. Once the workflow is placed here, it will be displayed in the web console on the workflow page. 

### Validating Workflows

To validate your workflows, navigate to the bottom of the workflow page and click `Validate Workflows`. After a brief time you will be redirected to a page very similar to the first, but containing only valid workflows that Gator Computational Cloud has identified will execute as expected.

### Executing Workflows

On the workflow page, any workflow that is displayed will contain an `Execute` button. To execute this workflow and produce the expected output result in your Dropbox account, click this button. This process is non-blocking so you will be redirected to the same page once the execution task is spawned. Initially, a folder called `exec` will be created in the workflow base folder in your Dropbox account. Once the execution is complete, this folder will be filled with logs and output data (if applicable). 

## Designing Workflows

The design of workflows for execution using Gator Computational Cloud is quite simple. It is very important for these workflows to be configured properly as, if they are not, they will execute improperly and possibly waste computing resources and time. A valid workflow consists of many aspects.

The first aspect of a workflow, which is optional, is the `data` folder. In this folder, the initial data that is needed by the workflow is stored. For example, in a text analysis workflow, this directory would consist of textual data that is distributed to any node that requires it. Without this folder, the workflow would need to read in data from an external source such as a database, which is still entirely valid. In this case, the `data` folder can be removed as long as it is specified that no nodes require any files from it. The next optional workflow feature is the `pem` folder. PEM stands for privacy-enhanced mail, and it is a type of certificate that ensures an SSH connection is secure in the context of GCC. This folder is necessary only if a virtual machine is specifically assigned to a certain task, in which case the user can then specify a PEM file as well. This file should be located in the `pem` folder and, without it, the task would execute with an error.

```
<?xml version="1.0"?>
<workflow type="0">
    <task id="n1">
	    <dep>words.txt</dep>
    </task>
    <task id="n2">
	    <dep node="n1">wc1_1.txt</dep>
    </task>
    <task id="n3">
        <dep node="n1">wc1_2.txt</dep>
    </task>
    <task id="n4">
	    <dep node="n2">wc2.txt</dep>
	    <dep node="n3">wc3.txt</dep>
    </task>
</workflow>
```

The rest of the workflow aspects are required for the successful execution of a workflow. The first of these is the `nodes` folder. Within this folder sits a multitude of zip files corresponding to tasks specified within the specification XML file. These zip files contain four main components; an `src` folder consisting of Python source files, a `requirements.txt` file specifying any Python dependencies that the project needs to execute properly, and a `data` folder containing both an `in` and `out` directory to direct data flow between nodes. On top of the nodes folder, a valid workflow also requires a specification XML file titled `spec.xml`. This specification file is similar to that shown above; however, it will change from workflow to workflow depending on each workflow's needs. In this specific scenario, the workflow, named wf1, does not contain the optional `pem` folder, however, it contains all the required items and the optional data folder as well.